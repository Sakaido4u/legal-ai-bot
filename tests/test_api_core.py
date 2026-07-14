"""Core product-loop API tests (auth, history, analyze, admin, health)."""

from slowapi.errors import RateLimitExceeded


def _register(client, email: str = "user@example.com", password: str = "Testpass1"):
    return client.post(
        "/auth/register",
        json={"name": "Test User", "email": email, "password": password},
    )


def test_register_and_login(client):
    reg = _register(client)
    assert reg.status_code == 200, reg.text
    body = reg.json()
    assert body["access_token"]
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["is_admin"] is False

    bad = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401

    ok = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "Testpass1"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]


def test_forgot_password_dev_returns_token(client):
    email = "reset@example.com"
    _register(client, email=email)
    res = client.post("/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert data["reset_token"]
    assert "issued" in data["message"].lower() or "reset" in data["message"].lower()


def test_analyze_requires_auth(client):
    res = client.post(
        "/v1/compliance/analyze",
        json={
            "query": "Is GDPR consent needed for marketing email?",
            "product_feature": "Email marketing",
            "jurisdictions": ["GDPR"],
        },
    )
    assert res.status_code in (401, 403)


def test_upload_requires_auth(client):
    res = client.post(
        "/documents/upload",
        data={"jurisdiction": "GDPR", "title": "t"},
        files={"file": ("doc.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert res.status_code in (401, 403)


def test_analyze_and_history(client):
    token = _register(client, email="analyst@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    analyze = client.post(
        "/v1/compliance/analyze",
        headers=headers,
        json={
            "query": "Is GDPR consent needed for marketing email?",
            "product_feature": "Email marketing",
            "jurisdictions": ["GDPR"],
        },
    )
    assert analyze.status_code == 200, analyze.text
    payload = analyze.json()
    assert payload["compliance_score"] == 80
    assert payload["risk_level"] == "low"

    history = client.get("/v1/compliance/history", headers=headers)
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) >= 1
    assert rows[0]["compliance_score"] == 80


def test_admin_seeded_and_list(client):
    # Seeded admin from lifespan
    login = client.post(
        "/auth/login",
        json={"email": "admin@lexai.com", "password": "Admin@1234"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["user"]["is_admin"] is True
    token = login.json()["access_token"]

    res = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    assert res.json()["total"] >= 1


def test_admin_list_requires_admin(client):
    token = _register(client, email="plain@example.com").json()["access_token"]
    res = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_health_includes_database_and_index(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert "database" in body
    assert body["database"]["status"] in ("ok", "error")
    assert "index_vectors" in body or "index" in body


def test_rate_limit_handler_registered(client):
    from backend.main import app

    assert RateLimitExceeded in app.exception_handlers


def test_auth_rate_limit_429():
    """Isolated tiny FastAPI app to confirm slowapi returns 429."""
    from starlette.requests import Request
    from starlette.responses import PlainTextResponse
    from starlette.testclient import TestClient as StarletteClient
    from fastapi import FastAPI
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    lim = Limiter(key_func=get_remote_address, default_limits=[], storage_uri="memory://")
    app = FastAPI()
    app.state.limiter = lim
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    @lim.limit("2/minute")
    async def ping(request: Request):
        return PlainTextResponse("ok")

    c = StarletteClient(app)
    r = c.get("/ping")
    assert r.status_code == 200, r.text
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 429
