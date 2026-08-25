from __future__ import annotations

import hashlib
import re
from typing import Iterator

from .schemas import ChunkRecord, Jurisdiction

_WS = re.compile(r"\s+")
# Split on sentence-ending punctuation followed by whitespace / end.
# Also treat numbered legal clauses ("1. ", "(a) ") as soft boundaries when packing.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[;:])\s+(?=[A-Z(])")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentence/clause units without cutting mid-word."""
    t = _norm(text)
    if not t:
        return []
    parts = [p.strip() for p in _SENTENCE_END.split(t) if p.strip()]
    return parts or [t]


def _pack_sentences(
    sentences: list[str],
    *,
    chunk_size: int,
    overlap_sentences: int = 1,
) -> list[str]:
    """Pack whole sentences into chunks ≤ chunk_size chars (soft overflow for one long sentence)."""
    if not sentences:
        return []

    chunks: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        chunks.append(" ".join(buf))
        if overlap_sentences > 0 and len(buf) > overlap_sentences:
            buf = buf[-overlap_sentences:]
            buf_len = sum(len(s) for s in buf) + max(0, len(buf) - 1)
        else:
            buf = []
            buf_len = 0

    for sent in sentences:
        sent_len = len(sent)
        # Single sentence longer than window — keep intact (never mid-word slice).
        if not buf and sent_len >= chunk_size:
            chunks.append(sent)
            continue
        extra = sent_len + (1 if buf else 0)
        if buf and buf_len + extra > chunk_size:
            flush()
        buf.append(sent)
        buf_len += extra

    if buf:
        # Final flush without carrying overlap forward.
        chunks.append(" ".join(buf))

    return chunks


def trim_orphaned_edges(text: str) -> str:
    """
    Drop leading/trailing fragments that look like mid-sentence leftovers
    (e.g. starts with lowercase after a prior window cut).
    """
    t = text.strip()
    if not t:
        return t
    # If we start mid-word / mid-clause with lowercase, cut to first capital sentence start.
    if t[0].islower():
        m = re.search(r"(?:(?<=[.!?]\s)|(?<=;\s))([A-Z(])", t)
        if m:
            t = t[m.start(1) :]
        else:
            # Fall back: drop until first whitespace after a short orphan prefix.
            sp = t.find(" ")
            if 0 < sp < 40:
                t = t[sp + 1 :].lstrip()
    # If we end mid-word without terminal punctuation, trim back to last sentence end.
    if t and t[-1] not in ".!?;:)]\"'":
        last = max(t.rfind(". "), t.rfind("? "), t.rfind("! "), t.rfind("; "))
        if last >= int(len(t) * 0.4):
            t = t[: last + 1].strip()
    return t.strip()


def chunk_text(
    *,
    text: str,
    jurisdiction: Jurisdiction,
    source_label: str,
    heading: str | None,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[ChunkRecord]:
    """
    Sentence-aware chunking with light overlap.

    ``chunk_overlap`` is interpreted as an approximate character budget for
    overlapping prior sentences (not a raw character slide).
    """
    t = _norm(text)
    if not t:
        return []

    sentences = split_sentences(t)
    overlap_sentences = 1 if chunk_overlap > 0 else 0
    if chunk_overlap >= 200:
        overlap_sentences = 2

    pieces = _pack_sentences(sentences, chunk_size=chunk_size, overlap_sentences=overlap_sentences)
    out: list[ChunkRecord] = []
    for i, piece in enumerate(pieces):
        cleaned = trim_orphaned_edges(piece)
        if len(cleaned.split()) < 8 and out:
            # Append tiny leftover onto previous chunk rather than emit a stub.
            prev = out[-1]
            merged = trim_orphaned_edges(f"{prev.text} {cleaned}")
            out[-1] = prev.model_copy(update={"text": merged})
            continue
        if not cleaned:
            continue
        h = hashlib.sha256(
            f"{jurisdiction}:{source_label}:{i}:{cleaned[:80]}".encode()
        ).hexdigest()[:16]
        cid = f"{jurisdiction.value}-{h}"
        out.append(
            ChunkRecord(
                chunk_id=cid,
                jurisdiction=jurisdiction,
                source_label=source_label,
                heading=heading,
                text=cleaned,
            )
        )
    return out


def iter_batches(items: list[ChunkRecord], batch_size: int) -> Iterator[list[ChunkRecord]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]
