"""Stage-level latency profile of HighPrecisionRetriever.retrieve().

Reports, per question, the time spent in: query/sub-query encoding, FAISS
search, article de-duplication, and the MMR step (split into candidate
re-encoding vs. the MMR selection loop).  Also times the retriever after the
re-encoding fix (vectors reconstructed from the FAISS index).
"""

from __future__ import annotations

import json
import statistics
import time

import numpy as np

from common import BASE_MODEL, INDEX_DIR, RESULTS, dump_json

import faiss  # noqa: F401  (import before torch on Windows)

from ml.embeddings import EmbeddingBackend
from ml.query_expand import decompose_query
from ml.retriever import HighPrecisionRetriever, _dedupe_by_article, _mmr_select
from ml.schemas import Jurisdiction
from ml.vector_store import ComplianceVectorStore


def profile_once(retriever: HighPrecisionRetriever, query: str, jurisdictions, top_k: int) -> dict:
    """Re-implements retrieve() step by step with timers (mirrors the original code path)."""
    t = {}
    t0 = time.perf_counter()
    subqueries = decompose_query(query)
    pool_k = max(top_k * retriever.pool_multipler, top_k)
    by_chunk = {}
    enc = 0.0
    search = 0.0
    for sq in subqueries:
        a = time.perf_counter()
        qv = retriever.embedder.encode([sq])[0]
        b = time.perf_counter()
        hits = retriever.store.search(qv, jurisdictions=list(jurisdictions), top_k=pool_k, min_score=retriever.min_score)
        c = time.perf_counter()
        enc += b - a
        search += c - b
        for h in hits:
            prev = by_chunk.get(h.chunk_id)
            if prev is None or h.similarity > prev.similarity:
                by_chunk[h.chunk_id] = h
    t["encode_queries_ms"] = enc * 1000
    t["faiss_search_ms"] = search * 1000
    t["n_subqueries"] = len(subqueries)

    pool = sorted(by_chunk.values(), key=lambda p: p.similarity, reverse=True)
    a = time.perf_counter()
    pool = _dedupe_by_article(pool)
    t["dedupe_ms"] = (time.perf_counter() - a) * 1000
    t["pool_after_dedupe"] = len(pool)

    if len(pool) > top_k:
        a = time.perf_counter()
        qv = retriever.embedder.encode([query])[0]
        b = time.perf_counter()
        cand_embs = retriever.embedder.encode([p.text for p in pool])
        c = time.perf_counter()
        _mmr_select(qv, pool, cand_embs, top_n=top_k, lambda_mult=retriever.mmr_lambda)
        d = time.perf_counter()
        t["mmr_reencode_query_ms"] = (b - a) * 1000
        t["mmr_reencode_candidates_ms"] = (c - b) * 1000
        t["mmr_select_loop_ms"] = (d - c) * 1000
    else:
        t["mmr_reencode_query_ms"] = t["mmr_reencode_candidates_ms"] = t["mmr_select_loop_ms"] = 0.0
    t["total_ms"] = (time.perf_counter() - t0) * 1000
    return t


def main(tag: str) -> None:
    questions = json.loads((RESULTS.parent / "questions.json").read_text(encoding="utf-8"))["questions"]
    embedder = EmbeddingBackend(BASE_MODEL)
    store = ComplianceVectorStore.load(INDEX_DIR)
    retriever = HighPrecisionRetriever(store, embedder)

    # Warm-up (model load / first inference).
    retriever.retrieve("warm up query about consent", [Jurisdiction.GDPR], top_k=8)

    rows = []
    for q in questions:
        js = [Jurisdiction(j) for j in q["jurisdictions"]]
        rows.append({"id": q["id"], **profile_once(retriever, q["query"], js, top_k=8)})

    def agg(key):
        vals = [r[key] for r in rows]
        return {"mean": statistics.mean(vals), "median": statistics.median(vals), "sd": statistics.pstdev(vals)}

    summary = {k: agg(k) for k in rows[0] if k != "id"}

    # End-to-end wall clock: MMR on vs off (original implementation), repeated 3x.
    def wall(use_mmr: bool, reps: int = 3) -> dict:
        per = []
        for _ in range(reps):
            vals = []
            for q in questions:
                js = [Jurisdiction(j) for j in q["jurisdictions"]]
                a = time.perf_counter()
                retriever.retrieve(q["query"], js, top_k=8, use_mmr=use_mmr)
                vals.append((time.perf_counter() - a) * 1000)
            per.append(statistics.mean(vals))
        return {"mean_ms": statistics.mean(per), "sd_ms": statistics.pstdev(per)}

    e2e = {"mmr_on": wall(True), "mmr_off": wall(False)}

    # Equivalence check: MMR selection from re-encoded candidate text vs. vectors
    # reconstructed from the FAISS index must pick the same passages.
    mismatches = 0
    checked = 0
    if hasattr(store, "vectors_for"):
        for q in questions:
            js = [Jurisdiction(j) for j in q["jurisdictions"]]
            qv = embedder.encode([q["query"]])[0]
            pool = store.search(qv, jurisdictions=js, top_k=32, min_score=retriever.min_score)
            pool = _dedupe_by_article(pool)
            if len(pool) <= 8:
                continue
            checked += 1
            a = _mmr_select(qv, pool, embedder.encode([p.text for p in pool]), top_n=8, lambda_mult=retriever.mmr_lambda)
            b = _mmr_select(qv, pool, store.vectors_for(pool), top_n=8, lambda_mult=retriever.mmr_lambda)
            if [p.chunk_id for p in a] != [p.chunk_id for p in b]:
                mismatches += 1
    e2e["equivalence_check"] = {"questions_checked": checked, "selection_mismatches": mismatches}

    out = {"tag": tag, "per_question": rows, "stage_summary_ms": summary, "end_to_end": e2e}
    dump_json(out, RESULTS / f"mmr_profile_{tag}.json")
    print(json.dumps({"tag": tag, "stage_summary_ms": summary, "end_to_end": e2e}, indent=2))


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else "current")
