from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import Settings
from backend.deps import get_engine, get_settings
from backend.rag_service import RAGEngine
from backend.rate_limit import UPLOAD_LIMIT, limiter
from database import crud
from database.session import get_db
from ml.schemas import Jurisdiction
from services.document_service import (
    delete_document_and_reindex,
    document_to_dict,
    process_document_upload,
)
from services.query_service import run_legal_query
from services.risk_service import run_risk_analysis

from .schemas import (
    DeleteResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    LegalQueryRequest,
    LegalQueryResponse,
    RiskAnalysisRequest,
    RiskAnalysisResponse,
)

logger = logging.getLogger(__name__)

# All routes on this router require a valid JWT (Bearer token).
router = APIRouter(
    tags=["compliance"],
    dependencies=[Depends(get_current_user)],
)


def _parse_jurisdictions(raw: list[str]) -> list[Jurisdiction]:
    try:
        return [Jurisdiction(j) for j in raw]
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid jurisdiction: {exc}",
        ) from exc


@router.post("/documents/upload", response_model=DocumentUploadResponse)
@limiter.limit(UPLOAD_LIMIT)
async def upload_document(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    engine: Annotated[RAGEngine, Depends(get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: UploadFile = File(...),
    jurisdiction: str = Form(...),
    title: str | None = Form(default=None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF uploads are supported in v1.",
        )

    js = _parse_jurisdictions([jurisdiction])

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    try:
        doc = await asyncio.to_thread(
            process_document_upload,
            db,
            engine,
            file_bytes=content,
            filename=file.filename,
            jurisdiction=js[0],
            title=title,
            settings=settings,
        )

    except Exception as exc:
        logger.exception("upload_failure filename=%s", file.filename)

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {exc}",
        ) from exc

    return DocumentUploadResponse(
        **document_to_dict(doc)
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    docs = crud.list_documents(
        db,
        skip=skip,
        limit=min(limit, 200),
    )

    return DocumentListResponse(
        documents=[
            DocumentUploadResponse(
                **document_to_dict(document)
            )
            for document in docs
        ],
        total=len(docs),
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
)
def get_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    doc = crud.get_document(
        db,
        document_id,
    )

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return DocumentDetailResponse(
        **document_to_dict(
            doc,
            include_sections=True,
        )
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
)
async def delete_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    engine: Annotated[RAGEngine, Depends(get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    doc = crud.get_document(
        db,
        document_id,
    )

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    await asyncio.to_thread(
        delete_document_and_reindex,
        db,
        engine,
        doc,
        settings,
    )

    return DeleteResponse(
        id=document_id,
        deleted=True,
        message=(
            "Document and associated metadata removed; "
            "FAISS index rebuilt."
        ),
    )


@router.post(
    "/legal_query",
    response_model=LegalQueryResponse,
)
async def legal_query(
    body: LegalQueryRequest,
    db: Annotated[Session, Depends(get_db)],
    engine: Annotated[RAGEngine, Depends(get_engine)],
):
    if engine.store.is_empty():
        raise HTTPException(
            status_code=503,
            detail=(
                "Vector index is empty. Upload documents or set "
                "COMPLIANCE_USE_DEMO_INDEX=true."
            ),
        )

    if (
        body.document_id is not None
        and crud.get_document(
            db,
            body.document_id,
        )
        is None
    ):
        raise HTTPException(
            status_code=404,
            detail="Referenced document not found.",
        )

    jurisdictions = _parse_jurisdictions(
        body.jurisdictions
    )

    result = await asyncio.to_thread(
        run_legal_query,
        db,
        engine,
        question=body.question,
        product_feature=body.product_feature,
        jurisdictions=jurisdictions,
        document_id=body.document_id,
        top_k=body.top_k,
    )

    return LegalQueryResponse(
        **result
    )


@router.post(
    "/risk_analysis",
    response_model=RiskAnalysisResponse,
)
async def risk_analysis(
    body: RiskAnalysisRequest,
    db: Annotated[Session, Depends(get_db)],
    engine: Annotated[RAGEngine, Depends(get_engine)],
):
    if engine.store.is_empty():
        raise HTTPException(
            status_code=503,
            detail=(
                "Vector index is empty. Upload documents or set "
                "COMPLIANCE_USE_DEMO_INDEX=true."
            ),
        )

    if (
        body.document_id is not None
        and crud.get_document(
            db,
            body.document_id,
        )
        is None
    ):
        raise HTTPException(
            status_code=404,
            detail="Referenced document not found.",
        )

    jurisdictions = _parse_jurisdictions(
        body.jurisdictions
    )

    result = await asyncio.to_thread(
        run_risk_analysis,
        db,
        engine,
        query=body.query,
        product_feature=body.product_feature,
        jurisdictions=jurisdictions,
        document_id=body.document_id,
        top_k=body.top_k,
    )

    return RiskAnalysisResponse(
        **result
    )