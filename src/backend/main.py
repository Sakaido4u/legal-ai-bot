from __future__ import annotations

import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import crud
from database.models import User
from database.session import SessionLocal, get_db, init_db
from ml.ollama_health import check_ollama_llm
from ml.schemas import Jurisdiction

from .analysis_summary import summarize_jurisdictions
from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from .config import Settings
from .deps import get_engine, set_engine
from .email_service import send_password_reset_email
from .middleware import RequestLoggingMiddleware
from .rag_service import RAGEngine, build_engine, run_compliance_analysis
from .rate_limit import ANALYZE_LIMIT, AUTH_LIMIT, limiter
from .routes import router
from .schemas import (
    AdminUserListResponse,
    AdminUserOut,
    AnalysisDetailResponse,
    AnalysisHistoryItem,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUserOut,
    ComplianceAnalyzeRequest,
    ComplianceAnalyzeResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

_boot_settings = Settings()
_started_at = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    init_db()

    db = SessionLocal()
    try:
        crud.seed_demo_users(db, hash_password)
        logger.info("Demo users ready (demo@lexai.com / admin@lexai.com)")
    except Exception:
        db.rollback()
        logger.exception("Failed to seed demo users")
    finally:
        db.close()

    engine = build_engine(settings)
    set_engine(engine)
    logger.info("RAG engine ready (index vectors=%s)", engine.store.ntotal())
    if settings.llm_provider == "ollama":
        ollama = check_ollama_llm(settings.ollama_base_url, settings.llm_model)
        if ollama["status"] != "ok":
            logger.warning("Ollama LLM degraded: %s", ollama)
        else:
            logger.info("Ollama LLM ready: model=%s", settings.llm_model)
    yield
    set_engine(None)


app = FastAPI(
    title="Legal AI Compliance Assistant",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _boot_settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def _auth_response(user: User, settings: Settings | None = None) -> AuthTokenResponse:
    cfg = settings or Settings()
    return AuthTokenResponse(
        access_token=create_access_token(
            user_id=user.id,
            email=user.email,
            settings=cfg,
        ),
        token_type="bearer",
        user=AuthUserOut(
            id=str(user.id),
            name=user.name,
            email=user.email,
            is_admin=bool(user.is_admin),
        ),
    )


@app.post("/auth/login", response_model=AuthTokenResponse)
@limiter.limit(AUTH_LIMIT)
async def auth_login(
    request: Request,
    body: AuthLoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    email = body.email.strip().lower()
    user = crud.get_user_by_email(db, email)
    if user is None or not verify_password(body.password, user.hashed_password):
        logger.warning("auth_failure event=login email=%s reason=invalid_credentials", email)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        logger.warning("auth_failure event=login email=%s reason=deactivated", email)
        raise HTTPException(status_code=403, detail="Account deactivated")
    return _auth_response(user)


@app.post("/auth/register", response_model=AuthTokenResponse)
@limiter.limit(AUTH_LIMIT)
async def auth_register(
    request: Request,
    body: AuthRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    email = body.email.strip().lower()
    if crud.get_user_by_email(db, email) is not None:
        logger.warning("auth_failure event=register email=%s reason=already_registered", email)
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(
        db,
        email=email,
        name=body.name.strip(),
        hashed_password=hash_password(body.password),
    )
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@app.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit(AUTH_LIMIT)
async def auth_forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    settings = Settings()
    email = body.email.strip().lower()
    user = crud.get_user_by_email(db, email)
    generic = ForgotPasswordResponse(
        message="If that email exists, a reset link has been issued.",
        reset_token=None,
    )
    if user is None:
        return generic

    raw = secrets.token_urlsafe(32)
    crud.create_password_reset_token(
        db,
        user_id=user.id,
        token=raw,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.commit()

    try:
        send_password_reset_email(to_email=user.email, reset_token=raw, settings=settings)
    except Exception:
        logger.exception("email_failure event=password_reset email=%s", user.email)
        if not settings.is_development:
            raise HTTPException(
                status_code=503,
                detail="Unable to send reset email. Try again shortly.",
            ) from None

    # Never leak the token outside development.
    return ForgotPasswordResponse(
        message=generic.message,
        reset_token=raw if settings.is_development else None,
    )


@app.post("/auth/reset-password")
@limiter.limit(AUTH_LIMIT)
async def auth_reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    row = crud.get_password_reset_token(db, body.token.strip())
    if row is None or row.used_at is not None:
        logger.warning("auth_failure event=reset_password reason=invalid_token")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        logger.warning("auth_failure event=reset_password reason=expired_token")
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = crud.get_user_by_id(db, row.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(body.new_password)
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Password updated. You can log in with your new password."}


@app.get("/admin/users", response_model=AdminUserListResponse)
async def admin_list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    rows = crud.list_users(db, limit=500)
    users = [
        AdminUserOut(
            id=str(u.id),
            name=u.name,
            email=u.email,
            is_admin=bool(u.is_admin),
            is_active=bool(u.is_active),
            created_at=u.created_at.isoformat() if u.created_at else "",
        )
        for u in rows
    ]
    return AdminUserListResponse(users=users, total=len(users))


@app.post("/admin/users/{user_id}/deactivate")
async def admin_deactivate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    crud.set_user_active(db, user, is_active=False)
    db.commit()
    return {"id": str(user.id), "is_active": False, "message": "User deactivated"}


@app.post("/admin/users/{user_id}/activate")
async def admin_activate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    crud.set_user_active(db, user, is_active=True)
    db.commit()
    return {"id": str(user.id), "is_active": True, "message": "User activated"}


@app.delete("/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    crud.delete_user(db, user)
    db.commit()
    return {"id": str(user_id), "deleted": True, "message": "User deleted"}


@app.get("/")
async def root():
    return {
        "service": "Legal AI Compliance Assistant",
        "docs": "/docs",
        "health": "/health",
        "auth": {
            "public": [
                "POST /auth/login",
                "POST /auth/register",
                "POST /auth/forgot-password",
                "POST /auth/reset-password",
                "GET /health",
                "GET /",
                "GET /v1/compliance/jurisdictions",
            ],
            "jwt_protected": [
                "POST /v1/compliance/analyze",
                "GET /v1/compliance/history",
                "POST /documents/upload",
                "GET /documents",
                "GET /documents/{id}",
                "DELETE /documents/{id}",
                "POST /legal_query",
                "POST /risk_analysis",
            ],
            "admin": [
                "GET /admin/users",
                "POST /admin/users/{id}/deactivate",
                "POST /admin/users/{id}/activate",
                "DELETE /admin/users/{id}",
            ],
        },
    }


def _check_db() -> dict:
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok"}
        finally:
            db.close()
    except Exception as exc:
        logger.exception("health_check database_unreachable")
        return {"status": "error", "detail": str(exc)}


@app.get("/health")
async def health():
    uptime = int((datetime.now(timezone.utc) - _started_at).total_seconds())
    db_health = _check_db()

    try:
        engine = get_engine()
    except HTTPException:
        status = "starting" if db_health["status"] == "ok" else "unhealthy"
        return {
            "status": status,
            "version": app.version,
            "uptime_seconds": uptime,
            "index_vectors": 0,
            "embedding_model": None,
            "database": db_health,
        }

    index_vectors = engine.store.ntotal()
    payload = {
        "status": "ok",
        "version": app.version,
        "uptime_seconds": uptime,
        "index_vectors": index_vectors,
        "embedding_model": engine.settings.embedding_model,
        "llm_provider": engine.settings.llm_provider,
        "llm_model": engine.settings.llm_model,
        "database": db_health,
        "index": {
            "status": "ok" if index_vectors > 0 or engine.settings.use_demo_index else "empty",
            "vectors": index_vectors,
            "use_demo_index": engine.settings.use_demo_index,
        },
    }
    if db_health["status"] != "ok":
        payload["status"] = "unhealthy"
    if engine.settings.llm_provider == "ollama":
        payload["ollama"] = check_ollama_llm(
            engine.settings.ollama_base_url,
            engine.settings.llm_model,
        )
        if payload["ollama"]["status"] != "ok" and payload["status"] == "ok":
            payload["status"] = "degraded"
    if payload.get("index", {}).get("status") == "empty" and payload["status"] == "ok":
        payload["status"] = "degraded"
    return payload


@app.get("/v1/compliance/history", response_model=list[AnalysisHistoryItem])
async def compliance_history(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    rows = crud.list_compliance_analyses(db, limit=200)
    return [
        AnalysisHistoryItem(
            id=str(row.id),
            query=row.query,
            jurisdiction=row.jurisdiction,
            compliance_score=row.compliance_score,
            risk_level=row.risk_level,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in rows
    ]


@app.post("/v1/compliance/analyze", response_model=ComplianceAnalyzeResponse)
@limiter.limit(ANALYZE_LIMIT)
async def compliance_analyze(
    request: Request,
    body: ComplianceAnalyzeRequest,
    engine: Annotated[RAGEngine, Depends(get_engine)],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    try:
        js = [Jurisdiction(j) for j in body.jurisdictions]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid jurisdiction: {e}") from e

    if engine.store.is_empty():
        logger.error("analyze_error reason=empty_index")
        raise HTTPException(
            status_code=503,
            detail="Vector index is empty. Ingest documents or set COMPLIANCE_USE_DEMO_INDEX=true.",
        )

    allowed_refs: set[str] | None = None
    product_feature = body.product_feature
    if body.document_id is not None:
        doc = crud.get_document(db, body.document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Referenced document not found.")
        allowed_refs = crud.get_chunk_vector_references_for_document(db, body.document_id)
        if not allowed_refs:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Document has no indexed chunks yet. Wait for processing to finish "
                    "or re-upload the PDF."
                ),
            )
        excerpt = crud.get_document_text_excerpt(db, body.document_id)
        if excerpt:
            product_feature = (
                f"{body.product_feature}\n\n--- Uploaded document excerpt ---\n{excerpt}"
            )[:2000]

    try:
        result = await asyncio.to_thread(
            run_compliance_analysis,
            engine,
            query=body.query,
            product_feature=product_feature,
            jurisdictions=js,
            top_k=body.top_k,
            document_id=body.document_id,
            allowed_chunk_refs=allowed_refs,
        )
    except Exception:
        logger.exception("analyze_error query=%s", body.query[:80])
        raise

    try:
        # Make JSON-serializable for Postgres storage + History → Results reload.
        serializable: dict[str, Any] = json.loads(json.dumps(result, default=str))
        row = crud.create_compliance_analysis(
            db,
            query=body.query,
            jurisdiction=summarize_jurisdictions(body.jurisdictions),
            compliance_score=int(result.get("compliance_score", 0)),
            risk_level=str(result.get("risk_level", "low")),
            result_json=json.dumps(serializable),
        )
        db.commit()
        meta = serializable.setdefault("meta", {})
        if isinstance(meta, dict):
            meta["analysis_id"] = row.id
        result = serializable
    except Exception:
        db.rollback()
        logger.exception("Failed to persist compliance analysis history row")

    return result


@app.get("/v1/compliance/history/{analysis_id}", response_model=AnalysisDetailResponse)
async def compliance_history_detail(
    analysis_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    row = crud.get_compliance_analysis(db, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if not row.result_json:
        raise HTTPException(
            status_code=404,
            detail="Full analysis payload not available for this history row. Re-run the analysis.",
        )
    try:
        payload = json.loads(row.result_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Stored analysis payload is corrupt") from exc
    return AnalysisDetailResponse(
        id=str(row.id),
        created_at=row.created_at.isoformat() if row.created_at else "",
        result=payload,
    )


@app.get("/v1/compliance/jurisdictions")
async def list_jurisdictions():
    return {"jurisdictions": [j.value for j in Jurisdiction]}
