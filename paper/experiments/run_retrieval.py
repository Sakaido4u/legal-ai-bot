"""Retrieval baselines and ablations on the 80-question benchmark.

Configurations
  system        dense, jurisdiction-partitioned, floor 0.22, query expansion, article dedupe, MMR
  no_mmr        system without the MMR re-ranker
  no_dedupe     system without article-level de-duplication
  no_expansion  system without multi-aspect query expansion
  no_floor      system without the similarity floor
  global_index  system but searching all jurisdictions regardless of the request
  bm25          lexical BM25 over the same chunks (partitioned)
  hybrid_rrf    reciprocal-rank fusion of dense and BM25 candidate lists
  fixed_chunks  system pipeline over fixed-size 900/120-char windows instead of hierarchy-aware chunks
  finetuned     system pipeline with the domain-adapted MiniLM encoder (146 pairs, 2 epochs)

Relevance is judged at the statutory-unit level (GDPR Article / DPDP Section /
CCPA topic) using the position-based chunk map from build_gold.py.
"""

from __future__ import annotations

import json
import math
import re
import time
from collections import Counter, defaultdict

import numpy as np

from common import (
    BASE_MODEL,
    FINETUNED_MODEL,
    INDEX_DIR,
    PDFS,
    RESULTS,
    NormalizedDoc,
    bootstrap_ci,
    dpdp_section_boundaries,
    dump_json,
    gdpr_article_boundaries,
    labels_spanning,
    load_meta,
    load_pdf_text,
)

import faiss  # noqa: F401  (import before torch on Windows)

from ml.embeddings import EmbeddingBackend
from ml.query_expand import decompose_query
from ml.retriever import HighPrecisionRetriever, _dedupe_by_article, _mmr_select
from ml.schemas import ChunkRecord, Jurisdiction, RetrievedPassage
from ml.vector_store import ComplianceVectorStore

TOP_K = 8
K_EVAL = (4, 8)
MIN_SCORE = 0.22
MMR_LAMBDA = 0.55
POOL_MULT = 4
ALL_J = [Jurisdiction.GDPR, Jurisdiction.DPDP, Jurisdiction.CCPA]

_TOK = re.compile(r"[a-z0-9]+")


def tokenize(s: str) -> list[str]:
    return _TOK.findall(s.lower())


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.toks = [tokenize(d) for d in docs]
        self.dl = np.array([len(t) for t in self.toks], dtype=float)
        self.avgdl = float(self.dl.mean()) if len(docs) else 0.0
        df: Counter = Counter()
        for t in self.toks:
            df.update(set(t))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.tf = [Counter(t) for t in self.toks]

    def scores(self, query: str) -> np.ndarray:
        q = tokenize(query)
        out = np.zeros(len(self.toks))
        for i, tf in enumerate(self.tf):
            s = 0.0
            denom_c = self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
            for w in q:
                f = tf.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + denom_c)
            out[i] = s
        return out


class Corpus:
    """Chunks + unit labels + dense store + BM25 for one chunking/encoder variant."""

    def __init__(self, name: str, chunks: list[ChunkRecord], units: dict[str, list[str]], embedder: EmbeddingBackend, embs: np.ndarray | None = None) -> None:
        self.name = name
        self.chunks = chunks
        self.units = units
        self.embedder = embedder
        self.store = ComplianceVectorStore(embedder.dim)
        if embs is None:
            embs = embedder.encode([c.text for c in chunks])
        self.store.add(embs, chunks)
        self.bm25 = {j: BM25([c.text for c in chunks if c.jurisdiction == j]) for j in ALL_J}
        self.bm25_chunks = {j: [c for c in chunks if c.jurisdiction == j] for j in ALL_J}


def to_passage(c: ChunkRecord, sim: float) -> RetrievedPassage:
    return RetrievedPassage(chunk_id=c.chunk_id, jurisdiction=c.jurisdiction, source_label=c.source_label, heading=c.heading, text=c.text, similarity=sim)


def bm25_search(corpus: Corpus, query: str, jurisdictions, k: int) -> list[RetrievedPassage]:
    hits = []
    for j in jurisdictions:
        sc = corpus.bm25[j].scores(query)
        order = np.argsort(-sc)[:k]
        for i in order:
            if sc[i] <= 0:
                continue
            hits.append(to_passage(corpus.bm25_chunks[j][i], float(sc[i])))
    hits.sort(key=lambda p: p.similarity, reverse=True)
    return hits[:k]


def dense_pipeline(corpus: Corpus, query: str, jurisdictions, *, top_k=TOP_K, expansion=True, floor=MIN_SCORE, dedupe=True, mmr=True, search_j=None) -> list[RetrievedPassage]:
    """Mirror of HighPrecisionRetriever.retrieve with switchable stages."""
    subqueries = decompose_query(query) if expansion else [query]
    pool_k = max(top_k * POOL_MULT, top_k)
    by_chunk: dict[str, RetrievedPassage] = {}
    primary = None
    for sq in subqueries:
        qv = corpus.embedder.encode([sq])[0]
        if primary is None:
            primary = qv
        for h in corpus.store.search(qv, jurisdictions=list(search_j or jurisdictions), top_k=pool_k, min_score=floor):
            prev = by_chunk.get(h.chunk_id)
            if prev is None or h.similarity > prev.similarity:
                by_chunk[h.chunk_id] = h
    pool = sorted(by_chunk.values(), key=lambda p: p.similarity, reverse=True)
    if not pool:
        return []
    if dedupe:
        pool = _dedupe_by_article(pool)
    if len(pool) <= top_k or not mmr:
        return pool[:top_k]
    vecs = corpus.store.vectors_for(pool)
    return _mmr_select(primary, pool, vecs, top_n=top_k, lambda_mult=MMR_LAMBDA)


def hybrid_rrf(corpus: Corpus, query: str, jurisdictions, top_k=TOP_K, k_rrf: int = 60) -> list[RetrievedPassage]:
    dense = dense_pipeline(corpus, query, jurisdictions, top_k=top_k * POOL_MULT, dedupe=False, mmr=False)
    lex = bm25_search(corpus, query, jurisdictions, top_k * POOL_MULT)
    score: dict[str, float] = defaultdict(float)
    obj: dict[str, RetrievedPassage] = {}
    for lst in (dense, lex):
        for r, p in enumerate(lst):
            score[p.chunk_id] += 1.0 / (k_rrf + r + 1)
            obj.setdefault(p.chunk_id, p)
    ranked = sorted(score, key=lambda c: -score[c])[:top_k]
    return [obj[c] for c in ranked]


def judge(hits: list[RetrievedPassage], gold: dict[str, list[str]], units: dict[str, list[str]], requested: list[str]) -> dict:
    rel = []
    for p in hits:
        g = set(gold.get(p.jurisdiction.value, []))
        u = set(units.get(p.chunk_id, []))
        rel.append(bool(g & u))
    out = {}
    for k in K_EVAL:
        out[f"hit@{k}"] = float(any(rel[:k]))
    first = next((i for i, r in enumerate(rel[:TOP_K]) if r), None)
    out["mrr@8"] = 0.0 if first is None else 1.0 / (first + 1)
    out["precision@8"] = float(sum(rel[:TOP_K]) / max(1, len(rel[:TOP_K]))) if hits else 0.0
    out["jurisdiction_precision"] = float(sum(1 for p in hits if p.jurisdiction.value in requested) / len(hits)) if hits else 0.0
    gj = [j for j in gold if j in requested]
    if gj:
        cov = [any(r for r, p in zip(rel[:TOP_K], hits[:TOP_K]) if p.jurisdiction.value == j) for j in gj]
        out["jurisdiction_coverage"] = float(sum(cov) / len(cov))
    out["n_retrieved"] = len(hits)
    out["max_sim"] = max((p.similarity for p in hits), default=0.0)
    return out


def build_fixed_chunks(embedder: EmbeddingBackend, base_chunks: list[ChunkRecord], base_units: dict[str, list[str]], size: int = 900, overlap: int = 120):
    chunks: list[ChunkRecord] = []
    units: dict[str, list[str]] = {}
    for j, pdf in PDFS.items():
        raw = load_pdf_text(pdf)
        nd = NormalizedDoc(raw)
        b = gdpr_article_boundaries(raw) if j == "GDPR" else dpdp_section_boundaries(raw)
        bn = [(nd.raw_to_norm(pos), lab) for pos, lab in b]
        text = nd.text
        start = 0
        i = 0
        while start < len(text):
            end = min(len(text), start + size)
            piece = text[start:end]
            cid = f"{j}-fixed-{i}"
            chunks.append(ChunkRecord(chunk_id=cid, jurisdiction=Jurisdiction(j), source_label=f"{j} fixed window {i}", heading=None, text=piece))
            units[cid] = labels_spanning(bn, start, end)
            i += 1
            if end >= len(text):
                break
            start = end - overlap
    # CCPA: same 7 HTML chunks in both variants
    for c in base_chunks:
        if c.jurisdiction == Jurisdiction.CCPA:
            chunks.append(c)
            units[c.chunk_id] = base_units[c.chunk_id]
    return chunks, units


def main() -> None:
    questions = json.loads((RESULTS.parent / "questions.json").read_text(encoding="utf-8"))["questions"]
    unit_map = json.loads((RESULTS / "chunk_unit_map.json").read_text(encoding="utf-8"))["chunks"]
    base_units = {cid: (v.get("units") or [v["unit"]]) if v["jurisdiction"] != "CCPA" else v.get("topics", []) for cid, v in unit_map.items()}

    embedder = EmbeddingBackend(BASE_MODEL)
    base_chunks: list[ChunkRecord] = []
    for j in ALL_J:
        for m in load_meta(INDEX_DIR, j.value):
            base_chunks.append(ChunkRecord(chunk_id=m["chunk_id"], jurisdiction=j, source_label=m["source_label"], heading=m.get("heading"), text=m["text"]))
    # Reuse stored vectors for the base corpus (identical to re-encoding; avoids a 712-chunk encode).
    loaded = ComplianceVectorStore.load(INDEX_DIR)
    base_vecs = loaded.vectors_for([to_passage(c, 0.0) for c in base_chunks])
    base = Corpus("hierarchy", base_chunks, base_units, embedder, embs=base_vecs)

    # Sanity: flexible pipeline must reproduce the production retriever exactly.
    prod = HighPrecisionRetriever(loaded, embedder)
    mism = 0
    for q in questions:
        js = [Jurisdiction(j) for j in q["jurisdictions"]]
        a = [p.chunk_id for p in prod.retrieve(q["query"], js, top_k=TOP_K)]
        b = [p.chunk_id for p in dense_pipeline(base, q["query"], js)]
        mism += a != b
    print(f"pipeline reproduction mismatches vs production retriever: {mism}/{len(questions)}")

    print("building fixed-size chunk corpus ...")
    fx_chunks, fx_units = build_fixed_chunks(embedder, base_chunks, base_units)
    fixed = Corpus("fixed", fx_chunks, fx_units, embedder)
    print(f"  fixed corpus: {len(fx_chunks)} chunks")

    print("encoding corpus with fine-tuned encoder ...")
    ft_embedder = EmbeddingBackend(str(FINETUNED_MODEL))
    finetuned = Corpus("finetuned", base_chunks, base_units, ft_embedder)

    # Error-analysis-driven variant: drop GDPR recital chunks (non-operative text) from the index.
    keep = [i for i, c in enumerate(base_chunks) if base_units.get(c.chunk_id) != ["Recital"]]
    op_chunks = [base_chunks[i] for i in keep]
    operative = Corpus("operative_only", op_chunks, base_units, embedder, embs=base_vecs[keep])
    print(f"  operative-only corpus: {len(op_chunks)} chunks (dropped {len(base_chunks) - len(op_chunks)} recital chunks)")

    configs = {
        "system": lambda q, js: dense_pipeline(base, q, js),
        "no_mmr": lambda q, js: dense_pipeline(base, q, js, mmr=False),
        "no_dedupe": lambda q, js: dense_pipeline(base, q, js, dedupe=False),
        "no_expansion": lambda q, js: dense_pipeline(base, q, js, expansion=False),
        "no_floor": lambda q, js: dense_pipeline(base, q, js, floor=-1.0),
        "global_index": lambda q, js: dense_pipeline(base, q, js, search_j=ALL_J),
        "bm25": lambda q, js: bm25_search(base, q, js, TOP_K),
        "hybrid_rrf": lambda q, js: hybrid_rrf(base, q, js),
        "fixed_chunks": lambda q, js: dense_pipeline(fixed, q, js),
        "finetuned": lambda q, js: dense_pipeline(finetuned, q, js),
        "no_recitals": lambda q, js: dense_pipeline(operative, q, js),
        "no_recitals_no_mmr": lambda q, js: dense_pipeline(operative, q, js, mmr=False),
        "no_recitals_hybrid": lambda q, js: hybrid_rrf(operative, q, js),
    }

    per_q: dict[str, list[dict]] = {}
    summary: dict[str, dict] = {}
    for name, fn in configs.items():
        rows = []
        t_all = []
        for q in questions:
            js = [Jurisdiction(j) for j in q["jurisdictions"]]
            t0 = time.perf_counter()
            hits = fn(q["query"], js)
            t_all.append((time.perf_counter() - t0) * 1000)
            units = fixed.units if name == "fixed_chunks" else base.units
            m = judge(hits, q["gold"], units, q["jurisdictions"])
            rows.append({"id": q["id"], "category": q["category"], **m, "top_units": [units.get(p.chunk_id, ["?"])[0] for p in hits[:TOP_K]]})
        per_q[name] = rows
        gold_rows = [r for r in rows if r["category"] != "negative"]
        neg_rows = [r for r in rows if r["category"] == "negative"]
        s = {"latency_ms_mean": float(np.mean(t_all))}
        for metric in ("hit@4", "hit@8", "mrr@8", "precision@8", "jurisdiction_precision"):
            mean, lo, hi = bootstrap_ci([r[metric] for r in gold_rows])
            s[metric] = {"mean": mean, "ci95": [lo, hi]}
        cov = [r["jurisdiction_coverage"] for r in gold_rows if "jurisdiction_coverage" in r and r["category"] == "cross"]
        if cov:
            mean, lo, hi = bootstrap_ci(cov)
            s["cross_jurisdiction_coverage"] = {"mean": mean, "ci95": [lo, hi]}
        s["by_category_hit@8"] = {}
        for cat in ("gdpr", "dpdp", "ccpa", "cross", "ambiguous"):
            vals = [r["hit@8"] for r in rows if r["category"] == cat]
            if vals:
                s["by_category_hit@8"][cat] = {"mean": float(np.mean(vals)), "n": len(vals)}
        s["negative"] = {
            "n": len(neg_rows),
            "returned_any_passage": float(np.mean([r["n_retrieved"] > 0 for r in neg_rows])) if neg_rows else None,
            "max_sim_mean": float(np.mean([r["max_sim"] for r in neg_rows])) if neg_rows else None,
            "flagged_low_confidence(<0.50)": float(np.mean([r["max_sim"] < 0.50 for r in neg_rows])) if neg_rows else None,
        }
        s["gold_questions_max_sim_mean"] = float(np.mean([r["max_sim"] for r in gold_rows]))
        g_rows = [r for r in rows if r["category"] in ("gdpr", "ambiguous") and r["top_units"]]
        s["recital_share_top8_gdpr_questions"] = float(np.mean([sum(u == "Recital" for u in r["top_units"]) / len(r["top_units"]) for r in g_rows])) if g_rows else None
        summary[name] = s
        print(f"{name:14s} hit@4={s['hit@4']['mean']:.3f} hit@8={s['hit@8']['mean']:.3f} mrr@8={s['mrr@8']['mean']:.3f} P@8={s['precision@8']['mean']:.3f} jP={s['jurisdiction_precision']['mean']:.3f} lat={s['latency_ms_mean']:.1f}ms")

    # Paired bootstrap of differences vs. system (hit@8 and mrr@8).
    rng = np.random.default_rng(0)
    base_rows = {r["id"]: r for r in per_q["system"] if r["category"] != "negative"}
    ids = list(base_rows)
    paired = {}
    for name in configs:
        if name == "system":
            continue
        other = {r["id"]: r for r in per_q[name]}
        paired[name] = {}
        for metric in ("hit@8", "mrr@8"):
            d = np.array([other[i][metric] - base_rows[i][metric] for i in ids])
            boots = d[rng.integers(0, len(d), size=(2000, len(d)))].mean(axis=1)
            paired[name][metric] = {"mean_diff": float(d.mean()), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}

    # Legacy 6-case keyword benchmark (as in the first draft), MMR on vs off, for continuity.
    from ml.benchmarks import DEFAULT_BENCHMARKS, run_retrieval_benchmark

    class _NoMMR(HighPrecisionRetriever):
        def retrieve(self, query, jurisdictions, *, top_k=8, use_mmr=True):  # noqa: D401
            return super().retrieve(query, jurisdictions, top_k=top_k, use_mmr=False)

    legacy = {
        "mmr_on": run_retrieval_benchmark(prod, DEFAULT_BENCHMARKS),
        "mmr_off": run_retrieval_benchmark(_NoMMR(loaded, embedder), DEFAULT_BENCHMARKS),
    }
    # Unit-level judgment of the same six cases (do keyword passes correspond to the right article?)
    legacy_gold = {
        "gdpr_special_categories": {"GDPR": ["Article 9"]},
        "dpdp_children_consent": {"DPDP": ["Section 9"]},
        "ccpa_sensitive_limit": {"CCPA": ["limit_sensitive_pi"]},
        "cross_jurisdiction_erasure": {"GDPR": ["Article 17"], "DPDP": ["Section 12"], "CCPA": ["right_to_delete"]},
        "gdpr_automated_decisions": {"GDPR": ["Article 22"]},
        "dpdp_data_fiduciary_obligations": {"DPDP": ["Section 8"]},
    }
    legacy["unit_level"] = {}
    for case in DEFAULT_BENCHMARKS:
        hits = prod.retrieve(case.query, case.jurisdictions, top_k=4, use_mmr=True)
        m = judge(hits, legacy_gold[case.name], base.units, [j.value for j in case.jurisdictions])
        legacy["unit_level"][case.name] = {"hit@4": m["hit@4"], "top_units": [base.units.get(p.chunk_id, ["?"])[0] for p in hits]}

    out = {
        "n_questions": len(questions),
        "n_gold_questions": len(ids),
        "top_k": TOP_K,
        "legacy_six_case_benchmark": legacy,
        "corpus_sizes": {"hierarchy": len(base_chunks), "fixed": len(fx_chunks), "operative_only": len(op_chunks)},
        "pipeline_reproduction_mismatches": mism,
        "summary": summary,
        "paired_diff_vs_system": paired,
        "per_question": per_q,
    }
    dump_json(out, RESULTS / "retrieval_results.json")
    print("saved", RESULTS / "retrieval_results.json")


if __name__ == "__main__":
    main()
