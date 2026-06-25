from __future__ import annotations

import hashlib
from typing import Protocol

from .chunking import chunk_text
from .schemas import ChunkRecord, Jurisdiction


class LegalSectionLike(Protocol):
    heading: str
    text: str


def _stable_chunk_id(jurisdiction: Jurisdiction, source_label: str, suffix: str) -> str:
    h = hashlib.sha256(f"{jurisdiction}:{source_label}:{suffix}".encode()).hexdigest()[:16]
    return f"{jurisdiction.value}-{h}"


def sections_to_chunks(
    sections: list[LegalSectionLike],
    *,
    jurisdiction: Jurisdiction,
    source_label: str,
    max_section_chars: int = 1600,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[ChunkRecord]:
    """
    Convert hierarchy-aware sections (PDF or web) into embeddable chunks.

    Short sections stay intact (preserves Article/Section boundaries).
    Long sections fall back to overlapping windows under the same heading.
    """
    out: list[ChunkRecord] = []
    for i, section in enumerate(sections):
        heading = (section.heading or "").strip() or None
        body = (section.text or "").strip()
        if not body or len(body.split()) < 3:
            continue

        label = f"{source_label} | {heading}" if heading else source_label

        if len(body) <= max_section_chars:
            cid = _stable_chunk_id(jurisdiction, label, f"sec{i}:{body[:80]}")
            out.append(
                ChunkRecord(
                    chunk_id=cid,
                    jurisdiction=jurisdiction,
                    source_label=label,
                    heading=heading,
                    text=body,
                )
            )
            continue

        parts = chunk_text(
            text=body,
            jurisdiction=jurisdiction,
            source_label=label,
            heading=heading,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        for part_idx, piece in enumerate(parts):
            piece.chunk_id = _stable_chunk_id(jurisdiction, label, f"sec{i}:part{part_idx}:{piece.text[:60]}")
            piece.source_label = f"{label} (part {part_idx + 1})"
            out.append(piece)

    return out
