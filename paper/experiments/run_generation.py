"""Citation-bound generation benchmark with refusal diagnosis.

For every question: retrieve top-k passages with the production retriever,
then run the production prompt/validator loop against an Ollama model while
logging the raw text of every attempt.  Outcomes are categorised so that
refusals can be attributed to (a) the model emitting REFUSE, (b) hallucinated
citation ids, (c) uncited sentences, or (d) sentence-splitter artefacts that
the fixed validator no longer rejects.

Usage:  python run_generation.py <ollama-model> <run-tag> [top_k]
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter

import requests

from common import BASE_MODEL, INDEX_DIR, RESULTS, dump_json

import faiss  # noqa: F401

from ml.embeddings import EmbeddingBackend
from ml.llm_backend import _build_citation_prompt
from ml.llm_citations import (
    _SENTENCE_SPLIT,
    extract_citation_ids,
    passages_to_citations,
    split_validation_sentences,
    substantive_lines,
    validate_citation_coverage,
)
from ml.retriever import HighPrecisionRetriever
from ml.schemas import Jurisdiction
from ml.vector_store import ComplianceVectorStore

OLLAMA = "http://127.0.0.1:11434"


def ollama_chat(model: str, system: str, user: str, timeout: float = 180.0) -> tuple[str, float, dict]:
    t0 = time.perf_counter()
    resp = requests.post(
        f"{OLLAMA}/api/chat",
        json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "stream": False, "options": {"temperature": 0.1}},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    meta = {k: data.get(k) for k in ("eval_count", "prompt_eval_count", "eval_duration", "prompt_eval_duration", "total_duration")}
    return str(data["message"]["content"]).strip(), (time.perf_counter() - t0) * 1000, meta


_MALFORMED_TAG = re.compile(r"\(C\d+\)|\bC\d+\b(?![\]\)])")


def per_sentence_ok(answer: str, allowed: set[str], splitter, *, skip_headers: bool) -> tuple[bool, str]:
    """Returns (ok, reason) where reason in {ok, no_substantive, uncited_sentence, invalid_id, header_line}."""
    lines = substantive_lines(answer, skip_list_introducers=skip_headers)
    if not lines:
        return False, "no_substantive"
    for line in lines:
        if line.endswith(":") and not extract_citation_ids(line):
            return False, "header_line"
        for part in splitter(line):
            part = part.strip()
            if len(part) < 12:
                continue
            refs = extract_citation_ids(part)
            if not refs:
                return False, "malformed_tag" if _MALFORMED_TAG.search(part) else "uncited_sentence"
            if not refs <= allowed:
                return False, "invalid_id"
    return True, "ok"


def legacy_split(text: str) -> list[str]:
    return _SENTENCE_SPLIT.split(text)


def diagnose(raw: str, allowed: set[str]) -> dict:
    d = {"raw_len": len(raw)}
    if not raw.strip():
        d["kind"] = "empty"
        return d
    if raw.upper().startswith("REFUSE"):
        d["kind"] = "refuse_token"
        return d
    used = extract_citation_ids(raw)
    d["citations_used"] = sorted(used)
    d["invalid_ids"] = sorted(used - allowed)
    d["id_only_ok"] = validate_citation_coverage(raw, allowed)
    variants = {
        "legacy": (legacy_split, False),
        "splitter_fix": (split_validation_sentences, False),
        "header_fix": (legacy_split, True),
        "both_fixes": (split_validation_sentences, True),
    }
    for name, (sp, hdr) in variants.items():
        ok, reason = per_sentence_ok(raw, allowed, sp, skip_headers=hdr)
        d[f"ok_{name}"] = ok
        d[f"reason_{name}"] = reason
    # Production validator == both fixes.
    d["per_sentence_ok_fixed"] = d["ok_both_fixes"]
    d["per_sentence_ok_legacy"] = d["ok_legacy"]
    if d["ok_both_fixes"]:
        d["kind"] = "valid"
    elif d["invalid_ids"]:
        d["kind"] = "invalid_citation_id"
    else:
        d["kind"] = d["reason_both_fixes"]
    d["legacy_kind"] = "valid" if d["ok_legacy"] else ("invalid_citation_id" if d["invalid_ids"] else d["reason_legacy"])
    d["n_bullets"] = len(substantive_lines(raw))
    return d


def main(model: str, tag: str, top_k: int) -> None:
    questions = json.loads((RESULTS.parent / "questions.json").read_text(encoding="utf-8"))["questions"]
    embedder = EmbeddingBackend(BASE_MODEL)
    store = ComplianceVectorStore.load(INDEX_DIR)
    retriever = HighPrecisionRetriever(store, embedder)

    # Warm-up so that model load time is not counted in the first question's latency.
    try:
        ollama_chat(model, "You are a helpful assistant.", "Reply with the single word: ready")
    except Exception as exc:  # noqa: BLE001
        print("warm-up failed:", exc)

    rows = []
    for qi, q in enumerate(questions):
        js = [Jurisdiction(j) for j in q["jurisdictions"]]
        hits = retriever.retrieve(q["query"], js, top_k=top_k, use_mmr=True)
        cits = passages_to_citations(hits)
        allowed = {c.citation_id for c in cits}
        row = {
            "id": q["id"],
            "category": q["category"],
            "n_citations": len(cits),
            "max_sim": max((c.similarity for c in cits), default=0.0),
            "citations": [{"id": c.citation_id, "jurisdiction": c.jurisdiction.value, "source": c.source_label, "excerpt": c.excerpt} for c in cits],
            "attempts": [],
        }
        if not cits:
            row["outcome"] = "no_evidence_refusal"
            rows.append(row)
            print(f"[{qi+1}/{len(questions)}] {q['id']}: no evidence")
            continue

        outcome = None
        strict = False
        for attempt in range(2):
            system, user = _build_citation_prompt(query=q["query"], product_feature=q["product_feature"], citations=cits, strict=strict)
            try:
                raw, ms, meta = ollama_chat(model, system, user)
            except Exception as exc:  # noqa: BLE001
                row["attempts"].append({"attempt": attempt + 1, "error": str(exc)})
                outcome = "error"
                break
            d = diagnose(raw, allowed)
            row["attempts"].append({"attempt": attempt + 1, "strict": strict, "latency_ms": ms, "ollama": meta, "raw": raw, **d})
            if d["kind"] == "valid":
                outcome = "answered_first_try" if attempt == 0 else "answered_after_retry"
                break
            if d["kind"] in ("refuse_token", "empty"):
                outcome = "refuse_token" if d["kind"] == "refuse_token" else "empty"
                break
            strict = True
        if outcome is None:
            # both attempts failed validation -> production code refuses
            kinds = [a.get("kind") for a in row["attempts"]]
            outcome = "validator_refusal:" + "/".join(kinds)
        row["outcome"] = outcome
        row["total_latency_ms"] = sum(a.get("latency_ms", 0.0) for a in row["attempts"])
        rows.append(row)
        print(f"[{qi+1}/{len(questions)}] {q['id']}: {outcome} ({row['total_latency_ms']:.0f} ms)")

    # Summary
    gold_rows = [r for r in rows if r["category"] != "negative"]
    neg_rows = [r for r in rows if r["category"] == "negative"]

    def summarize(rs):
        c = Counter(r["outcome"].split(":")[0] for r in rs)
        answered = sum(1 for r in rs if r["outcome"].startswith("answered"))
        first = [a for r in rs for a in r["attempts"] if a.get("attempt") == 1 and "kind" in a]
        return {
            "n": len(rs),
            "answered": answered,
            "answer_rate": answered / len(rs) if rs else None,
            "refusal_rate": 1 - answered / len(rs) if rs else None,
            "outcomes": dict(c),
            "first_attempt_kinds": dict(Counter(a["kind"] for a in first)),
            "first_attempt_kinds_legacy_validator": dict(Counter(a.get("legacy_kind", a["kind"]) for a in first)),
            "first_attempt_pass_rate_id_only": sum(1 for a in first if a.get("id_only_ok")) / len(first) if first else None,
            "first_attempt_pass_rate_per_sentence_legacy": sum(1 for a in first if a.get("ok_legacy")) / len(first) if first else None,
            "first_attempt_pass_rate_per_sentence_splitter_fix": sum(1 for a in first if a.get("ok_splitter_fix")) / len(first) if first else None,
            "first_attempt_pass_rate_per_sentence_header_fix": sum(1 for a in first if a.get("ok_header_fix")) / len(first) if first else None,
            "first_attempt_pass_rate_per_sentence_fixed": sum(1 for a in first if a.get("ok_both_fixes")) / len(first) if first else None,
            "mean_latency_ms_per_call": sum(a["latency_ms"] for r in rs for a in r["attempts"] if "latency_ms" in a) / max(1, sum(1 for r in rs for a in r["attempts"] if "latency_ms" in a)),
            "mean_total_latency_ms": sum(r.get("total_latency_ms", 0) for r in rs) / len(rs) if rs else None,
            "by_category_refusal": {
                cat: 1 - sum(1 for r in rs if r["category"] == cat and r["outcome"].startswith("answered")) / max(1, sum(1 for r in rs if r["category"] == cat))
                for cat in sorted({r["category"] for r in rs})
            },
        }

    out = {
        "model": model,
        "tag": tag,
        "top_k": top_k,
        "validator_used_in_loop": "both_fixes",
        "summary_gold_questions": summarize(gold_rows),
        "summary_negative_questions": summarize(neg_rows),
        "rows": rows,
    }
    path = RESULTS / f"generation_{tag}.json"
    dump_json(out, path)
    print(json.dumps({"gold": out["summary_gold_questions"], "negative": out["summary_negative_questions"]}, indent=2))
    print("saved", path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
