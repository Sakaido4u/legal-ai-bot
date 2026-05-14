from __future__ import annotations

import hashlib
import re
from typing import Iterator

from .schemas import ChunkRecord, Jurisdiction

_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


def chunk_text(
    *,
    text: str,
    jurisdiction: Jurisdiction,
    source_label: str,
    heading: str | None,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[ChunkRecord]:
    """Character-window chunking with overlap; stable chunk_id from content hash."""
    t = _norm(text)
    if not t:
        return []

    step = max(1, chunk_size - chunk_overlap)
    out: list[ChunkRecord] = []
    for i, start in enumerate(range(0, len(t), step)):
        piece = t[start : start + chunk_size]
        if len(piece.split()) < 8 and out:
            break
        h = hashlib.sha256(f"{jurisdiction}:{source_label}:{start}:{piece[:80]}".encode()).hexdigest()[:16]
        cid = f"{jurisdiction.value}-{h}"
        out.append(
            ChunkRecord(
                chunk_id=cid,
                jurisdiction=jurisdiction,
                source_label=source_label,
                heading=heading,
                text=piece,
            )
        )
        if start + chunk_size >= len(t):
            break
    return out


def iter_batches(items: list[ChunkRecord], batch_size: int) -> Iterator[list[ChunkRecord]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]
