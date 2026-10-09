"""NLI-based claim-support evaluation of generated answers.

For each validated answer, every substantive sentence is treated as a claim.
Premise = the excerpt(s) the sentence cites; hypothesis = the sentence with
citation tags removed.  A cross-encoder NLI model scores entailment /
neutral / contradiction.  We also score each claim against *all* excerpts in
the prompt to separate "unsupported" from "supported but mis-cited".

Usage: python run_faithfulness.py generation_<tag>.json [more tags...]
"""

from __future__ import annotations

import json
import re
import sys

import numpy as np

from common import RESULTS, dump_json

import faiss  # noqa: F401

from sentence_transformers import CrossEncoder

from ml.llm_citations import extract_citation_ids, split_validation_sentences

NLI_MODEL = "cross-encoder/nli-deberta-v3-base"
_TAG = re.compile(r"\s*\[C\d+\]")


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def claims_from_answer(raw: str) -> list[tuple[str, set[str]]]:
    out = []
    for line in raw.splitlines():
        cleaned = re.sub(r"^[-*\u2022]\s*", "", line.strip()).strip()
        if len(cleaned) < 12:
            continue
        for part in split_validation_sentences(cleaned):
            part = part.strip()
            if len(part) < 12:
                continue
            refs = extract_citation_ids(part)
            hyp = _TAG.sub("", part).strip()
            # Drop pure headers like "Here are the key points:"
            if len(hyp.split()) < 4:
                continue
            out.append((hyp, refs))
    return out


def main(files: list[str]) -> None:
    model = CrossEncoder(NLI_MODEL)
    labels = {v: k for k, v in model.config.id2label.items()}  # name -> idx
    ent, neu, con = labels["entailment"], labels["neutral"], labels["contradiction"]

    all_out = {}
    for fname in files:
        gen = json.loads((RESULTS / fname).read_text(encoding="utf-8"))
        sentences = []
        for row in gen["rows"]:
            if not row["outcome"].startswith("answered"):
                continue
            final = next(a for a in reversed(row["attempts"]) if a.get("kind") == "valid")
            excerpts = {c["id"]: c["excerpt"] for c in row["citations"]}
            for hyp, refs in claims_from_answer(final["raw"]):
                cited = [excerpts[r] for r in refs if r in excerpts]
                if not cited:
                    continue
                pairs_cited = [(p, hyp) for p in cited]
                pairs_all = [(p, hyp) for p in excerpts.values()]
                probs_cited = softmax(np.asarray(model.predict(pairs_cited)))
                probs_all = softmax(np.asarray(model.predict(pairs_all)))
                best_c = probs_cited[np.argmax(probs_cited[:, ent])]
                best_a = probs_all[np.argmax(probs_all[:, ent])]
                sentences.append(
                    {
                        "qid": row["id"],
                        "category": row["category"],
                        "claim": hyp,
                        "cited": sorted(refs),
                        "p_entail_cited": float(best_c[ent]),
                        "p_neutral_cited": float(best_c[neu]),
                        "p_contra_cited": float(best_c[con]),
                        "label_cited": ["contradiction", "entailment", "neutral"][int(np.argmax(best_c[[con, ent, neu]]))],
                        "p_entail_any": float(best_a[ent]),
                        "label_any": ["contradiction", "entailment", "neutral"][int(np.argmax(best_a[[con, ent, neu]]))],
                    }
                )
        if not sentences:
            all_out[fname] = {"n_claims": 0}
            continue
        lab = [s["label_cited"] for s in sentences]
        lab_any = [s["label_any"] for s in sentences]
        by_q = {}
        for s in sentences:
            by_q.setdefault(s["qid"], []).append(s["label_cited"] == "entailment")
        summary = {
            "model": gen["model"],
            "n_answers": len(by_q),
            "n_claims": len(sentences),
            "claims_per_answer": len(sentences) / len(by_q),
            "entailed_by_cited_excerpt": lab.count("entailment") / len(lab),
            "neutral_wrt_cited_excerpt": lab.count("neutral") / len(lab),
            "contradicted_by_cited_excerpt": lab.count("contradiction") / len(lab),
            "entailed_by_any_excerpt": lab_any.count("entailment") / len(lab_any),
            "supported_but_miscited": sum(1 for a, b in zip(lab, lab_any) if a != "entailment" and b == "entailment") / len(lab),
            "mean_p_entail_cited": float(np.mean([s["p_entail_cited"] for s in sentences])),
            "answers_fully_entailed": sum(1 for v in by_q.values() if all(v)) / len(by_q),
            "by_category_entailed": {
                cat: sum(1 for s in sentences if s["category"] == cat and s["label_cited"] == "entailment") / max(1, sum(1 for s in sentences if s["category"] == cat))
                for cat in sorted({s["category"] for s in sentences})
            },
        }
        all_out[fname] = {"summary": summary, "claims": sentences}
        print(fname, json.dumps(summary, indent=2))

    dump_json(all_out, RESULTS / "faithfulness.json")
    print("saved", RESULTS / "faithfulness.json")


if __name__ == "__main__":
    main(sys.argv[1:])
