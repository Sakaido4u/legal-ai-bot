from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .models import (
    AnalysisLog,
    Chunk,
    ComplianceAnalysisRecord,
    Document,
    PasswordResetToken,
    ProcessingStatus,
    Section,
    User,
)


def get_document(db: Session, document_id: int) -> Document | None:
    stmt = (
        select(Document)
        .options(joinedload(Document.sections).joinedload(Section.chunks))
        .where(Document.id == document_id)
    )
    return db.scalars(stmt).unique().first()


def get_document_by_sha256(db: Session, sha256: str) -> Document | None:
    return db.scalars(select(Document).where(Document.sha256 == sha256)).first()


def list_documents(db: Session, *, skip: int = 0, limit: int = 100) -> list[Document]:
    stmt = select(Document).order_by(Document.upload_date.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def create_document(
    db: Session,
    *,
    filename: str,
    title: str | None,
    jurisdiction: str,
    source_type: str,
    sha256: str,
    local_path: str | None = None,
    source_url: str | None = None,
    processing_status: str = ProcessingStatus.PENDING.value,
) -> Document:
    doc = Document(
        filename=filename,
        title=title,
        jurisdiction=jurisdiction,
        source_type=source_type,
        sha256=sha256,
        local_path=local_path,
        source_url=source_url,
        processing_status=processing_status,
    )
    db.add(doc)
    db.flush()
    return doc


def update_document_status(
    db: Session,
    document: Document,
    *,
    status: str,
    error_message: str | None = None,
) -> Document:
    document.processing_status = status
    document.error_message = error_message
    db.flush()
    return document


def delete_document(db: Session, document: Document) -> None:
    db.delete(document)
    db.flush()


def create_section(
    db: Session,
    *,
    document_id: int,
    section_id: int,
    heading: str | None,
    numeric_id: str | None,
    depth: int,
    parent_id: int | None,
) -> Section:
    section = Section(
        document_id=document_id,
        section_id=section_id,
        heading=heading,
        numeric_id=numeric_id,
        depth=depth,
        parent_id=parent_id,
    )
    db.add(section)
    db.flush()
    return section


def create_chunk(
    db: Session,
    *,
    section_id: int,
    chunk_index: int,
    text: str,
    word_count: int,
    char_count: int,
    vector_reference: str,
) -> Chunk:
    chunk = Chunk(
        section_id=section_id,
        chunk_index=chunk_index,
        text=text,
        word_count=word_count,
        char_count=char_count,
        vector_reference=vector_reference,
    )
    db.add(chunk)
    db.flush()
    return chunk


def get_all_chunk_records(db: Session) -> list[tuple[Chunk, str]]:
    """Return (chunk, jurisdiction) pairs for all indexed chunks."""
    stmt = (
        select(Chunk, Document.jurisdiction)
        .join(Section, Chunk.section_id == Section.id)
        .join(Document, Section.document_id == Document.id)
        .where(Document.processing_status == ProcessingStatus.COMPLETED.value)
    )
    return list(db.execute(stmt).all())


def get_chunk_vector_references_for_document(db: Session, document_id: int) -> set[str]:
    stmt = (
        select(Chunk.vector_reference)
        .join(Section, Chunk.section_id == Section.id)
        .where(Section.document_id == document_id)
    )
    return set(db.scalars(stmt).all())


def get_document_text_excerpt(db: Session, document_id: int, *, max_chars: int = 2000) -> str:
    """Concatenate chunk text from an uploaded document (for grounding product_feature)."""
    stmt = (
        select(Chunk.text)
        .join(Section, Chunk.section_id == Section.id)
        .where(Section.document_id == document_id)
        .order_by(Section.id.asc(), Chunk.chunk_index.asc())
    )
    parts: list[str] = []
    total = 0
    for text in db.scalars(stmt).all():
        if total >= max_chars:
            break
        piece = text.strip()
        if not piece:
            continue
        remain = max_chars - total
        parts.append(piece[:remain])
        total += len(parts[-1])
    return "\n\n".join(parts)


def create_analysis_log(
    db: Session,
    *,
    question: str,
    response_time: float,
    document_id: int | None = None,
    timestamp: datetime | None = None,
) -> AnalysisLog:
    log = AnalysisLog(
        document_id=document_id,
        question=question,
        response_time=response_time,
    )
    if timestamp is not None:
        log.timestamp = timestamp
    db.add(log)
    db.flush()
    return log


def create_compliance_analysis(
    db: Session,
    *,
    query: str,
    jurisdiction: str,
    compliance_score: int,
    risk_level: str,
) -> ComplianceAnalysisRecord:
    row = ComplianceAnalysisRecord(
        query=query,
        jurisdiction=jurisdiction,
        compliance_score=compliance_score,
        risk_level=risk_level,
    )
    db.add(row)
    db.flush()
    return row


def list_compliance_analyses(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[ComplianceAnalysisRecord]:
    stmt = (
        select(ComplianceAnalysisRecord)
        .order_by(ComplianceAnalysisRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


# ── Users / auth ────────────────────────────────────────────────

def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email.lower())).first()


def create_user(
    db: Session,
    *,
    email: str,
    name: str,
    hashed_password: str,
) -> User:
    user = User(
        email=email.strip().lower(),
        name=name.strip(),
        hashed_password=hashed_password,
    )
    db.add(user)
    db.flush()
    return user


def create_password_reset_token(
    db: Session,
    *,
    user_id: int,
    token: str,
    expires_at: datetime,
) -> PasswordResetToken:
    row = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(row)
    db.flush()
    return row


def get_password_reset_token(db: Session, token: str) -> PasswordResetToken | None:
    return db.scalars(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    ).first()


def seed_demo_users(db: Session, hash_fn) -> None:
    """Create demo accounts if missing (idempotent)."""
    demos = [
        ("demo@lexai.com", "Demo User", "Demo@1234"),
        ("admin@lexai.com", "Admin User", "Admin@1234"),
    ]
    for email, name, password in demos:
        if get_user_by_email(db, email) is None:
            create_user(db, email=email, name=name, hashed_password=hash_fn(password))
    db.commit()
