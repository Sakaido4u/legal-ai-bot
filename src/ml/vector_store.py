from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from .schemas import ChunkRecord, Jurisdiction, RetrievedPassage

logger = logging.getLogger(__name__)


class ComplianceVectorStore:
    """
    One FAISS IndexFlatIP per jurisdiction (L2-normalized vectors → cosine via IP).
    Metadata is kept in parallel lists aligned with FAISS row order.
    """

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self._indices: dict[Jurisdiction, faiss.IndexFlatIP] = {}
        self._metas: dict[Jurisdiction, list[dict[str, Any]]] = {}
        for j in Jurisdiction:
            self._indices[j] = faiss.IndexFlatIP(dim)
            self._metas[j] = []

    def is_empty(self) -> bool:
        return all(self._indices[j].ntotal == 0 for j in Jurisdiction)

    def ntotal(self) -> int:
        return sum(self._indices[j].ntotal for j in Jurisdiction)

    def add(self, embeddings: np.ndarray, chunks: list[ChunkRecord]) -> None:
        if embeddings.shape[0] != len(chunks):
            raise ValueError("embeddings and chunks length mismatch")
        if embeddings.shape[1] != self.dim:
            raise ValueError(f"expected dim {self.dim}, got {embeddings.shape[1]}")

        by_j: dict[Jurisdiction, list[tuple[np.ndarray, ChunkRecord]]] = {j: [] for j in Jurisdiction}
        for row, ch in zip(embeddings, chunks, strict=True):
            by_j[ch.jurisdiction].append((row, ch))

        for j, pairs in by_j.items():
            if not pairs:
                continue
            mat = np.stack([p[0] for p in pairs]).astype(np.float32, copy=False)
            self._indices[j].add(mat)
            self._metas[j].extend(
                {
                    "chunk_id": p[1].chunk_id,
                    "source_label": p[1].source_label,
                    "heading": p[1].heading,
                    "text": p[1].text,
                }
                for p in pairs
            )

    def search(
        self,
        query_vec: np.ndarray,
        *,
        jurisdictions: list[Jurisdiction],
        top_k: int = 8,
        min_score: float = 0.22,
    ) -> list[RetrievedPassage]:
        """Returns merged hits across jurisdictions, sorted by similarity descending."""
        if query_vec.ndim == 1:
            q = query_vec.astype(np.float32, copy=False).reshape(1, -1)
        else:
            q = query_vec.astype(np.float32, copy=False)

        hits: list[RetrievedPassage] = []
        for j in jurisdictions:
            index = self._indices[j]
            if index.ntotal == 0:
                continue
            k = min(top_k, int(index.ntotal))
            sims, idxs = index.search(q, k)
            for sim, row_i in zip(sims[0], idxs[0], strict=True):
                if row_i < 0:
                    continue
                if float(sim) < min_score:
                    continue
                meta = self._metas[j][int(row_i)]
                hits.append(
                    RetrievedPassage(
                        chunk_id=meta["chunk_id"],
                        jurisdiction=j,
                        source_label=meta["source_label"],
                        heading=meta.get("heading"),
                        text=meta["text"],
                        similarity=float(sim),
                    )
                )

        hits.sort(key=lambda h: h.similarity, reverse=True)
        return hits

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, Any] = {"dim": self.dim, "jurisdictions": {}}
        for j in Jurisdiction:
            path = directory / f"index_{j.value}.faiss"
            meta_path = directory / f"meta_{j.value}.jsonl"
            faiss.write_index(self._indices[j], str(path))
            with meta_path.open("w", encoding="utf-8") as f:
                for row in self._metas[j]:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            manifest["jurisdictions"][j.value] = {"index": path.name, "meta": meta_path.name}
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        logger.info("Saved vector store to %s", directory)

    @classmethod
    def load(cls, directory: Path) -> ComplianceVectorStore:
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"No manifest at {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dim = int(manifest["dim"])
        store = cls(dim)
        for j in Jurisdiction:
            info = manifest["jurisdictions"].get(j.value)
            if not info:
                continue
            idx_path = directory / info["index"]
            meta_path = directory / info["meta"]
            store._indices[j] = faiss.read_index(str(idx_path))
            metas: list[dict[str, Any]] = []
            if meta_path.is_file():
                for line in meta_path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        metas.append(json.loads(line))
            store._metas[j] = metas
        logger.info("Loaded vector store from %s (%d vectors)", directory, store.ntotal())
        return store
