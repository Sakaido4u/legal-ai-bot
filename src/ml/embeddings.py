from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> SentenceTransformer:
    logger.info("Loading sentence-transformers model: %s", model_name)
    return SentenceTransformer(model_name)


class EmbeddingBackend:
    """L2-normalized embeddings for cosine similarity via inner product."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = _load_model(model_name)
        dim_fn = getattr(self._model, "get_embedding_dimension", None) or getattr(
            self._model, "get_sentence_embedding_dimension", None
        )
        if dim_fn is None:
            self.dim = 384
        else:
            self.dim = int(dim_fn())

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        embs = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embs.astype(np.float32, copy=False)
