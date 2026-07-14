from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .chunking import iter_batches
from .embeddings import EmbeddingBackend
from .legal_chunking import sections_to_chunks
from .schemas import ChunkRecord, Jurisdiction
from .vector_store import ComplianceVectorStore

logger = logging.getLogger(__name__)

SourceType = Literal["url", "pdf", "html", "text"]

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@dataclass
class CorpusSource:
    jurisdiction: Jurisdiction
    source_type: SourceType
    label: str
    url: str | None = None
    path: str | None = None
    heading: str | None = None
    text: str | None = None


def load_corpus_seeds(path: Path) -> list[CorpusSource]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[CorpusSource] = []
    for row in raw.get("sources", []):
        out.append(
            CorpusSource(
                jurisdiction=Jurisdiction(row["jurisdiction"]),
                source_type=row["type"],
                label=row["label"],
                url=row.get("url"),
                path=row.get("path"),
                heading=row.get("heading"),
                text=row.get("text"),
            )
        )
    return out


def _chunks_from_url(source: CorpusSource) -> list[ChunkRecord]:
    from processing.web_scrapper import extract_text_from_url

    if not source.url:
        raise ValueError(f"URL source missing url: {source.label}")
    sections = extract_text_from_url(source.url)
    return sections_to_chunks(sections, jurisdiction=source.jurisdiction, source_label=source.label)


def _resolve_local_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    return p


def _chunks_from_html(source: CorpusSource) -> list[ChunkRecord]:
    from processing.web_scrapper import extract_structured_sections

    if not source.path:
        raise ValueError(f"HTML source missing path: {source.label}")
    html_path = _resolve_local_path(source.path)
    html = html_path.read_text(encoding="utf-8", errors="replace")
    source_url = source.url or f"file://{html_path.as_posix()}"
    sections = extract_structured_sections(html, source_url)
    return sections_to_chunks(sections, jurisdiction=source.jurisdiction, source_label=source.label)


def _chunks_from_pdf(source: CorpusSource) -> list[ChunkRecord]:
    from processing.pdf_parser import extract_legal_sections

    if not source.path:
        raise ValueError(f"PDF source missing path: {source.label}")
    pdf_path = _resolve_local_path(source.path)
    sections = extract_legal_sections(pdf_path)
    return sections_to_chunks(sections, jurisdiction=source.jurisdiction, source_label=source.label)


def _chunks_from_text(source: CorpusSource) -> list[ChunkRecord]:
    if not source.text:
        raise ValueError(f"Text source missing body: {source.label}")

    class _Section:
        def __init__(self, heading: str | None, text: str) -> None:
            self.heading = heading or ""
            self.text = text

    return sections_to_chunks(
        [_Section(source.heading, source.text)],
        jurisdiction=source.jurisdiction,
        source_label=source.label,
    )


def source_to_chunks(source: CorpusSource) -> list[ChunkRecord]:
    if source.source_type == "url":
        return _chunks_from_url(source)
    if source.source_type == "pdf":
        return _chunks_from_pdf(source)
    if source.source_type == "html":
        return _chunks_from_html(source)
    if source.source_type == "text":
        return _chunks_from_text(source)
    raise ValueError(f"Unknown source type: {source.source_type}")


def build_index_from_sources(
    sources: list[CorpusSource],
    *,
    embedding_model: str,
    output_dir: Path,
    batch_size: int = 32,
) -> dict[str, Any]:
    """Fetch/parse sources, embed, and persist a jurisdiction-aware FAISS index."""
    embedder = EmbeddingBackend(embedding_model)
    store = ComplianceVectorStore(embedder.dim)

    all_chunks: list[ChunkRecord] = []
    stats: dict[str, Any] = {"sources": [], "errors": []}

    for source in sources:
        try:
            chunks = source_to_chunks(source)
            all_chunks.extend(chunks)
            stats["sources"].append(
                {"label": source.label, "jurisdiction": source.jurisdiction.value, "chunks": len(chunks)}
            )
            logger.info("Ingested %s -> %d chunks", source.label, len(chunks))
        except Exception as exc:
            logger.exception("Failed source %s", source.label)
            stats["errors"].append({"label": source.label, "error": str(exc)})

    if not all_chunks:
        raise RuntimeError("No chunks produced; index not written.")

    texts = [c.text for c in all_chunks]
    for batch_start in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[batch_start : batch_start + batch_size]
        batch_texts = texts[batch_start : batch_start + batch_size]
        embs = embedder.encode(batch_texts)
        store.add(embs, batch_chunks)

    output_dir.mkdir(parents=True, exist_ok=True)
    store.save(output_dir)
    stats["total_chunks"] = len(all_chunks)
    stats["total_vectors"] = store.ntotal()
    stats["output_dir"] = str(output_dir)
    (output_dir / "ingest_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def build_index_from_seed_file(
    seed_path: Path,
    *,
    embedding_model: str,
    output_dir: Path,
) -> dict[str, Any]:
    sources = load_corpus_seeds(seed_path)
    return build_index_from_sources(sources, embedding_model=embedding_model, output_dir=output_dir)
