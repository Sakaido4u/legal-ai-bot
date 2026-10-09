"""Server-rendered demo flow: login -> query -> results -> PDF report.

Auth reuses the JWT helpers in backend.auth, but the token travels in an
HTTP-only cookie instead of an Authorization header, so plain HTML forms work.
Protected pages redirect to /demo/login when the cookie is missing or invalid.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.auth import create_access_token, decode_access_token, verify_password
from backend.config import Settings
from backend.deps import get_engine, get_settings
from backend.rag_service import RAGEngine
from backend.rate_limit import ANALYZE_LIMIT, AUTH_LIMIT, limiter
from database import crud
from database.models import User
from database.session import get_db
from services.demo_service import REGULATION_CHOICES, load_demo_result, run_demo_query
from services.pdf_report import DISCLAIMER, build_report_pdf

logger = logging.getLogger(__name__)

SESSION_COOKIE = "lexai_session"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["disclaimer"] = DISCLAIMER

router = APIRouter(prefix="/demo", tags=["demo"], include_in_schema=False)


def cookie_user(request: Request, db: Session) -> User | None:
    """The logged-in user from the session cookie, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        user_id = int(decode_access_token(token).get("sub", ""))
    except (HTTPException, ValueError):
        return None
    user = crud.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


def redirect_to_login() -> RedirectResponse:
    response = RedirectResponse("/demo/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
def demo_home(request: Request, db: Annotated[Session, Depends(get_db)]):
    return RedirectResponse("/demo/query" if cookie_user(request, db) else "/demo/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    if cookie_user(request, db):
        return RedirectResponse("/demo/query", status_code=303)
    return templates.TemplateResponse(request, "demo/login.html", {"error": None, "email": ""})


@router.post("/login", response_class=HTMLResponse)
@limiter.limit(AUTH_LIMIT)
def login_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
):
    email = email.strip().lower()
    user = crud.get_user_by_email(db, email) if email else None
    if user is None or not verify_password(password, user.hashed_password) or not user.is_active:
        logger.warning("auth_failure event=demo_login email=%s", email)
        return templates.TemplateResponse(
            request,
            "demo/login.html",
            {"error": "Invalid email or password.", "email": email},
            status_code=401,
        )

    token = create_access_token(user_id=user.id, email=user.email, settings=settings)
    response = RedirectResponse("/demo/query", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,  # not readable from JavaScript
        samesite="lax",  # not sent on cross-site form posts
        secure=not settings.is_development,  # HTTPS-only outside local development
        path="/",
    )
    return response


@router.post("/logout")
def logout():
    return redirect_to_login()


@router.get("/query", response_class=HTMLResponse)
def query_page(request: Request, db: Annotated[Session, Depends(get_db)]):
    user = cookie_user(request, db)
    if user is None:
        return redirect_to_login()
    return templates.TemplateResponse(
        request,
        "demo/query.html",
        {"user": user, "regulations": list(REGULATION_CHOICES), "error": None, "question": "", "regulation": "ALL"},
    )


@router.post("/query", response_class=HTMLResponse)
@limiter.limit(ANALYZE_LIMIT)
async def query_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    engine: Annotated[RAGEngine, Depends(get_engine)],
    question: Annotated[str, Form()] = "",
    regulation: Annotated[str, Form()] = "ALL",
):
    user = cookie_user(request, db)
    if user is None:
        return redirect_to_login()

    question = question.strip()
    error = None
    if not 3 <= len(question) <= 4000:
        error = "Please enter a question between 3 and 4000 characters."
    elif regulation not in REGULATION_CHOICES:
        error = "Please choose a regulation from the list."
    elif engine.store.is_empty():
        error = "The vector index is empty. Build it with scripts/build_corpus_index.py first."
    if error:
        return templates.TemplateResponse(
            request,
            "demo/query.html",
            {
                "user": user,
                "regulations": list(REGULATION_CHOICES),
                "error": error,
                "question": question,
                "regulation": regulation,
            },
            status_code=400,
        )

    analysis_id = await asyncio.to_thread(
        run_demo_query,
        db,
        engine,
        question=question,
        regulation=regulation,
        username=user.name or user.email,
    )
    # Post/Redirect/Get: refreshing the results page won't re-run the query.
    return RedirectResponse(f"/demo/results/{analysis_id}", status_code=303)


@router.get("/results/{analysis_id}", response_class=HTMLResponse)
def results_page(analysis_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    user = cookie_user(request, db)
    if user is None:
        return redirect_to_login()
    result = load_demo_result(db, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return templates.TemplateResponse(request, "demo/results.html", {"user": user, "r": result})


@router.get("/results/{analysis_id}/pdf")
def results_pdf(analysis_id: int, request: Request, db: Annotated[Session, Depends(get_db)]):
    if cookie_user(request, db) is None:
        return redirect_to_login()
    result = load_demo_result(db, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return Response(
        content=build_report_pdf(result),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="compliance-report-{analysis_id}.pdf"'},
    )
