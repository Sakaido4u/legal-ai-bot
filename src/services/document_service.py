from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.rag_service import RAGEngine
from database import crud
from database.models import Document, ProcessingStatus
from ml.legal_chunking import sections_to_chunks
from ml.schemas import ChunkRecord, Jurisdiction

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _vector_reference(jurisdiction: str, chunk_id: str) -> str:
    return f"{jurisdiction}:{chunk_id}"


def _resolve_upload_dir(settings: Settings) -> Path:
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.is_absolute():
        upload_dir = _REPO_ROOT / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _resolve_index_dir(settings: Settings) -> Path:
    if not settings.index_dir:
        raise ValueError("COMPLIANCE_INDEX_DIR is not configured")
    index_dir = Path(settings.index_dir)
    if not index_dir.is_absolute():
        index_dir = _REPO_ROOT / index_dir
    return index_dir


def _parse_pdf_sections(pdf_path: Path) -> list:
    from processing.pdf_parser import extract_legal_sections

    return extract_legal_sections(pdf_path)


def process_document_upload(
    db: Session,
    engine: RAGEngine,
    *,
    file_bytes: bytes,
    filename: str,
    jurisdiction: Jurisdiction,
    title: str | None,
    settings: Settings,
) -> Document:
    """
    Full upload pipeline: persist metadata → parse → chunk → embed → FAISS → DB records.
    """
    sha256 = _sha256_bytes(file_bytes)
    existing = crud.get_document_by_sha256(db, sha256)
    if existing is not None:
        return existing

    safe_name = Path(filename).name
    upload_dir = _resolve_upload_dir(settings)
    stored_path = upload_dir / f"{sha256[:16]}_{safe_name}"
    stored_path.write_bytes(file_bytes)

    doc = crud.create_document(
        db,
        filename=safe_name,
        title=title or safe_name,
        jurisdiction=jurisdiction.value,
        source_type="pdf",
        sha256=sha256,
        local_path=str(stored_path),
        processing_status=ProcessingStatus.PROCESSING.value,
    )
    db.commit()

    try:
        sections = _parse_pdf_sections(stored_path)
        source_label = title or safe_name
        total_chunks = 0
        skipped_chunks = 0
        pending_vectors: list[ChunkRecord] = []

        for legal_section in sections:
            db_section = crud.create_section(
                db,
                document_id=doc.id,
                section_id=legal_section.section_id,
                heading=legal_section.heading or None,
                numeric_id=legal_section.numeric_id,
                depth=legal_section.depth,
                parent_id=legal_section.parent_id,
            )

            chunk_records = sections_to_chunks(
                [legal_section],
                jurisdiction=jurisdiction,
                source_label=source_label,
            )

            for chunk_index, chunk_record in enumerate(chunk_records):
                vector_ref = _vector_reference(jurisdiction.value, chunk_record.chunk_id)

                # Each insert runs in its own SAVEPOINT (db.begin_nested()).
                # If this one chunk_id already exists (e.g. a duplicate
                # section detected by the parser), only THIS insert is
                # rolled back — the rest of the document's already-flushed
                # sections/chunks in this transaction are unaffected.
                # Without this, one duplicate poisons the whole Session
                # and kills the entire upload (the "transaction has been
                # rolled back" error).
                try:
                    with db.begin_nested():
                        crud.create_chunk(
                            db,
                            section_id=db_section.id,
                            chunk_index=chunk_index,
                            text=chunk_record.text,
                            word_count=len(chunk_record.text.split()),
                            char_count=len(chunk_record.text),
                            vector_reference=vector_ref,
                        )
                except IntegrityError:
                    logger.warning(
                        "Skipping duplicate chunk_id %s for document %d",
                        vector_ref,
                        doc.id,
                    )
                    skipped_chunks += 1
                    continue

                pending_vectors.append(chunk_record)
                total_chunks += 1

        crud.update_document_status(db, doc, status=ProcessingStatus.COMPLETED.value)
        db.commit()

        if skipped_chunks:
            logger.warning(
                "Document %d: skipped %d duplicate chunk(s) out of %d total",
                doc.id,
                skipped_chunks,
                total_chunks + skipped_chunks,
            )

        try:
            batch_size = 32
            for start in range(0, len(pending_vectors), batch_size):
                batch = pending_vectors[start : start + batch_size]
                embs = engine.embedder.encode([c.text for c in batch])
                engine.store.add(embs, batch)

            index_dir = _resolve_index_dir(settings)
            engine.store.save(index_dir)
        except Exception as faiss_exc:
            logger.exception("FAISS indexing failed for document %d; rebuilding from DB", doc.id)
            rebuild_faiss_index(db, engine, settings)
            if not pending_vectors:
                raise faiss_exc

        db.refresh(doc)
        logger.info(
            "Document %d processed: %d sections, %d chunks",
            doc.id,
            len(sections),
            total_chunks,
        )
        return doc

    except Exception as exc:
        logger.exception("Failed to process document %d", doc.id)
        db.rollback()
        doc = crud.get_document(db, doc.id) or doc
        crud.update_document_status(
            db,
            doc,
            status=ProcessingStatus.FAILED.value,
            error_message=str(exc),
        )
        db.commit()
        raise


def rebuild_faiss_index(db: Session, engine: RAGEngine, settings: Settings) -> int:
    """
    Rebuild the FAISS index from all completed documents in PostgreSQL.
    Used after document deletion to remove orphaned vectors.
    """
    from ml.schemas import Jurisdiction as JurisdictionEnum
    from ml.vector_store import ComplianceVectorStore

    rows = crud.get_all_chunk_records(db)
    store = ComplianceVectorStore(engine.embedder.dim)

    if not rows:
        index_dir = _resolve_index_dir(settings)
        store.save(index_dir)
        engine.store = store
        engine.retriever.store = store
        return 0

    chunk_records: list[ChunkRecord] = []
    texts: list[str] = []
    for chunk, jurisdiction_str in rows:
        j = JurisdictionEnum(jurisdiction_str)
        ref_parts = chunk.vector_reference.split(":", 1)
        chunk_id = ref_parts[1] if len(ref_parts) == 2 else chunk.vector_reference
        chunk_records.append(
            ChunkRecord(
                chunk_id=chunk_id,
                jurisdiction=j,
                source_label=f"doc-chunk-{chunk.id}",
                heading=None,
                text=chunk.text,
            )
        )
        texts.append(chunk.text)

    batch_size = 32
    for start in range(0, len(chunk_records), batch_size):
        batch_chunks = chunk_records[start : start + batch_size]
        batch_texts = texts[start : start + batch_size]
        embs = engine.embedder.encode(batch_texts)
        store.add(embs, batch_chunks)

    index_dir = _resolve_index_dir(settings)
    store.save(index_dir)
    engine.store = store
    engine.retriever.store = store
    return len(chunk_records)


def delete_document_and_reindex(
    db: Session,
    engine: RAGEngine,
    document: Document,
    settings: Settings,
) -> None:
    crud.delete_document(db, document)
    db.commit()
    rebuild_faiss_index(db, engine, settings)


def document_to_dict(doc: Document, *, include_sections: bool = False) -> dict:
    payload: dict = {
        "id": doc.id,
        "filename": doc.filename,
        "title": doc.title,
        "jurisdiction": doc.jurisdiction,
        "source_type": doc.source_type,
        "source_url": doc.source_url,
        "sha256": doc.sha256,
        "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
        "processing_status": doc.processing_status,
        "error_message": doc.error_message,
    }
    if include_sections:
        payload["sections"] = [
            {
                "id": s.id,
                "section_id": s.section_id,
                "heading": s.heading,
                "numeric_id": s.numeric_id,
                "depth": s.depth,
                "parent_id": s.parent_id,
                "chunks": [
                    {
                        "id": c.id,
                        "chunk_index": c.chunk_index,
                        "text": c.text[:500] + "..." if len(c.text) > 500 else c.text,
                        "word_count": c.word_count,
                        "char_count": c.char_count,
                        "vector_reference": c.vector_reference,
                    }
                    for c in s.chunks
                ],
            }
            for s in doc.sections
        ]
    return payload