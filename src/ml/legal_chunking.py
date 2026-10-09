from __future__ import annotations

import hashlib
import re
from typing import Protocol

from .chunking import chunk_text, trim_orphaned_edges
from .schemas import ChunkRecord, Jurisdiction

_PRIMARY_UNIT = re.compile(
    r"^(Article|Section|Clause)\s+(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)
_JUNK_HEADING = re.compile(
    r"^(?:"
    r"\d{1,2}\.\d{1,2}\.\d{4}"  # page dates like 4.5.2016
    r"|\d{1,2}\."  # bare "1." / "2." paragraph markers alone
    r"|OJ\b"
    r")",
    re.IGNORECASE,
)
_ARTICLE_REF_IN_TEXT = re.compile(r"\bArticle\s+(\d+[A-Za-z]?)\b", re.IGNORECASE)


class LegalSectionLike(Protocol):
    heading: str
    text: str


def _stable_chunk_id(jurisdiction: Jurisdiction, source_label: str, suffix: str) -> str:
    h = hashlib.sha256(f"{jurisdiction}:{source_label}:{suffix}".encode()).hexdigest()[:16]
    return f"{jurisdiction.value}-{h}"


def _is_junk_heading(heading: str) -> bool:
    h = (heading or "").strip()
    if not h:
        return False
    if _JUNK_HEADING.match(h):
        return True
    # Tiny lettered markers alone are not useful as standalone units.
    if re.fullmatch(r"\([a-zA-Z0-9]+\)", h):
        return True
    return False


def group_primary_legal_units(sections: list[LegalSectionLike]) -> list[tuple[str | None, str]]:
    """
    Merge PDF/HTML fragments under Article/Section primary headings.

    Recitals and other pre-article material are kept as standalone units when
    substantive; page-date / bare numeric junk headings are skipped (text may
    still attach to the current unit).
    """
    units: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_parts: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_parts
        body = trim_orphaned_edges(" ".join(p for p in current_parts if p.strip()))
        if body and len(body.split()) >= 8:
            units.append((current_heading, body))
        current_heading = None
        current_parts = []

    for section in sections:
        heading = (section.heading or "").strip()
        body = (section.text or "").strip()
        if not body:
            continue

        if _is_junk_heading(heading):
            # Keep body text with the open unit when we have one; else skip short junk.
            if current_parts and len(body.split()) >= 3:
                # Avoid re-including the junk heading line if it prefixes the body.
                cleaned = body
                if cleaned.lower().startswith(heading.lower()):
                    cleaned = cleaned[len(heading) :].strip()
                if cleaned:
                    current_parts.append(cleaned)
            continue

        primary = _PRIMARY_UNIT.match(heading)
        if primary:
            flush()
            current_heading = f"{primary.group(1).title()} {primary.group(2)}"
            # Prefer body without duplicating the heading line.
            cleaned = body
            if cleaned.lower().startswith(heading.lower()[: len(current_heading)]):
                # keep full body — article text often starts with "Article N\n1. ..."
                pass
            current_parts = [cleaned]
            continue

        if current_parts:
            current_parts.append(body)
            continue

        # Pre-article / unstructured material.
        if len(body.split()) >= 20:
            units.append((heading or None, trim_orphaned_edges(body)))

    flush()
    return units


def sections_to_chunks(
    sections: list[LegalSectionLike],
    *,
    jurisdiction: Jurisdiction,
    source_label: str,
    max_section_chars: int = 1800,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[ChunkRecord]:
    """
    Convert hierarchy-aware sections into embeddable chunks.

    Prefers Article/Section primary units. Short units stay intact; longer ones
    are split on sentence boundaries (never mid-word character windows).
    """
    units = group_primary_legal_units(sections)
    # Fallback: if grouping yielded nothing useful, use raw sections.
    if not units:
        units = []
        for section in sections:
            heading = (section.heading or "").strip() or None
            body = trim_orphaned_edges((section.text or "").strip())
            if body and len(body.split()) >= 3 and not _is_junk_heading(heading or ""):
                units.append((heading, body))

    out: list[ChunkRecord] = []
    for i, (heading, body) in enumerate(units):
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
            piece.chunk_id = _stable_chunk_id(
                jurisdiction, label, f"sec{i}:part{part_idx}:{piece.text[:60]}"
            )
            piece.source_label = f"{label} (part {part_idx + 1})"
            out.append(piece)

    return out


def article_key_from_text(*parts: str | None) -> str | None:
    """Extract a stable Article/Section key for deduplication, if present."""
    blob = " ".join(p for p in parts if p)
    m = _PRIMARY_UNIT.search(blob) or _ARTICLE_REF_IN_TEXT.search(blob)
    if not m:
        return None
    if m.lastindex and m.lastindex >= 2:
        return f"{m.group(1).title()} {m.group(2)}"
    return f"Article {m.group(1)}"
