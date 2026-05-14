from __future__ import annotations

import logging
from typing import Sequence

import numpy as np

from .embeddings import EmbeddingBackend
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


class HighPrecisionRetriever:
    """
    Retrieval tuned for compliance work:
    - per-jurisdiction FAISS search with a similarity floor
    - optional MMR rerank on the pooled shortlist
    """

    def __init__(
        self,
        store: ComplianceVectorStore,
        embedder: EmbeddingBackend,
        *,
        min_score: float = 0.22,
        pool_multipler: int = 3,
        mmr_lambda: float = 0.65,
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
        top_k: int = 6,
        use_mmr: bool = True,
    ) -> list[RetrievedPassage]:
        qv = self.embedder.encode([query])[0]
        pool_k = max(top_k * self.pool_multipler, top_k)
        pool = self.store.search(
            qv,
            jurisdictions=list(jurisdictions),
            top_k=pool_k,
            min_score=self.min_score,
        )
        if not pool:
            logger.info("Retriever: zero hits above min_score=%s", self.min_score)
            return []

        if not use_mmr or len(pool) <= top_k:
            return pool[:top_k]

        texts = [p.text for p in pool]
        cand_embs = self.embedder.encode(texts)
        return _mmr_select(qv, pool, cand_embs, top_n=top_k, lambda_mult=self.mmr_lambda)
