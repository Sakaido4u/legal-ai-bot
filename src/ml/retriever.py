from __future__ import annotations

import logging
import re
from typing import Sequence

import numpy as np

from .embeddings import EmbeddingBackend
from .legal_chunking import article_key_from_text
from .query_expand import decompose_query
from .schemas import Jurisdiction, RetrievedPassage
from .vector_store import ComplianceVectorStore

logger = logging.getLogger(__name__)


def _mmr_select(
    query_vec: np.ndarray,
    candidates: list[RetrievedPassage],
    cand_embs: np.ndarray,
    *,
    top_n: int,
    lambda_mult: float = 0.65,
) -> list[RetrievedPassage]:
    """
    Maximal Marginal Relevance: balance relevance vs diversity (reduces near-duplicate statutes).
    lambda_mult → 1.0 pure relevance, → 0.0 pure diversity.
    """
    if not candidates or top_n <= 0:
        return []
    q = query_vec.reshape(-1).astype(np.float32, copy=False)
    selected: list[int] = []
    remaining = set(range(len(candidates)))

    sim_to_query = cand_embs @ q

    while remaining and len(selected) < top_n:
        best_i = None
        best_score = -1e9
        for i in remaining:
            rel = float(sim_to_query[i])
            if not selected:
                mmr = rel
            else:
                div = max(float(cand_embs[i] @ cand_embs[j]) for j in selected)
                mmr = lambda_mult * rel - (1.0 - lambda_mult) * div
            if mmr > best_score:
                best_score = mmr
                best_i = i
        assert best_i is not None
        selected.append(best_i)
        remaining.remove(best_i)

    return [candidates[i] for i in selected]


def _dedupe_by_article(
    passages: list[RetrievedPassage],
    *,
    near_dup_sim: float = 0.92,
) -> list[RetrievedPassage]:
    """
    Keep the strongest hit per Article/Section key; also drop near-duplicate text
    chunks that lack an article key but are almost identical embeddings-wise
    (handled later by MMR — here we only key-dedupe + exact/near text).
    """
    best_by_key: dict[str, RetrievedPassage] = {}
    no_key: list[RetrievedPassage] = []
    for p in passages:
        key = article_key_from_text(p.heading, p.source_label, p.text[:240])
        if key:
            art_key = f"{p.jurisdiction.value}:{key}"
            prev = best_by_key.get(art_key)
            if prev is None or p.similarity > prev.similarity:
                best_by_key[art_key] = p
        else:
            no_key.append(p)

    # Light text-prefix dedupe for keyless passages.
    kept_no_key: list[RetrievedPassage] = []
    seen_prefixes: list[str] = []
    for p in sorted(no_key, key=lambda x: x.similarity, reverse=True):
        prefix = re.sub(r"\s+", " ", p.text[:160].lower())
        if any(_token_overlap(prefix, s) >= near_dup_sim for s in seen_prefixes):
            continue
        seen_prefixes.append(prefix)
        kept_no_key.append(p)

    merged = list(best_by_key.values()) + kept_no_key
    merged.sort(key=lambda p: p.similarity, reverse=True)
    return merged


def _token_overlap(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


class HighPrecisionRetriever:
    """
    Retrieval tuned for compliance work:
    - multi-aspect query expansion for compound legal questions
    - per-jurisdiction FAISS search with a similarity floor
    - article-level dedupe then optional MMR rerank
    """

    def __init__(
        self,
        store: ComplianceVectorStore,
        embedder: EmbeddingBackend,
        *,
        min_score: float = 0.22,
        pool_multipler: int = 4,
        mmr_lambda: float = 0.55,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.min_score = min_score
        self.pool_multipler = pool_multipler
        self.mmr_lambda = mmr_lambda

    def retrieve(
        self,
        query: str,
        jurisdictions: Sequence[Jurisdiction],
        *,
        top_k: int = 8,
        use_mmr: bool = True,
    ) -> list[RetrievedPassage]:
        subqueries = decompose_query(query)
        pool_k = max(top_k * self.pool_multipler, top_k)
        by_chunk: dict[str, RetrievedPassage] = {}
        primary_qv: np.ndarray | None = None

        for sq in subqueries:
            qv = self.embedder.encode([sq])[0]
            if primary_qv is None:
                primary_qv = qv  # decompose_query() always puts the full query first
            hits = self.store.search(
                qv,
                jurisdictions=list(jurisdictions),
                top_k=pool_k,
                min_score=self.min_score,
            )
            for h in hits:
                prev = by_chunk.get(h.chunk_id)
                if prev is None or h.similarity > prev.similarity:
                    by_chunk[h.chunk_id] = h

        pool = sorted(by_chunk.values(), key=lambda p: p.similarity, reverse=True)
        if not pool:
            logger.info("Retriever: zero hits above min_score=%s", self.min_score)
            return []

        pool = _dedupe_by_article(pool)
        if len(pool) <= top_k:
            return pool[:top_k]

        if not use_mmr:
            return pool[:top_k]

        # MMR against the primary (full) query embedding for final diversity.
        # Candidate vectors are read back from the index; the previous version
        # re-embedded candidate text here, which dominated retrieval latency.
        qv = primary_qv if primary_qv is not None else self.embedder.encode([query])[0]
        cand_embs = self.store.vectors_for(pool)
        if cand_embs is None:
            cand_embs = self.embedder.encode([p.text for p in pool])
        return _mmr_select(qv, pool, cand_embs, top_n=top_k, lambda_mult=self.mmr_lambda)
