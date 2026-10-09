"""Demo pages: cookie login, redirects, risk score on results, PDF report."""

import re

DEMO_EMAIL = "demo@lexai.com"  # seeded at startup (crud.seed_demo_users)
DEMO_PASSWORD = "Demo@1234"


def _fake_legal_query(db, engine, *, question, **kwargs):
    """Two hits above the 0.5 threshold, one below it (its high risk must be ignored)."""
    passages = [
        ("C0", 0.82, "Article 33", "high", 0.6),
        ("C1", 0.64, "(87)", "low", 0.1),
        ("C2", 0.31, "Article 99", "high", 0.9),
    ]
    return {
        "question": question,
        "answer": "Notify the supervisory authority within 72 hours [C0].",
        "citations": [
            {
                "citation_id": cid,
                "jurisdiction": "GDPR",
                "source_label": f"Regulation (EU) 2016/679 (GDPR) | {heading}",
                "heading": heading,
                "excerpt": f"{heading} excerpt text.",
                "similarity": sim,
            }
            for cid, sim, heading, _, _ in passages
        ],
        "risk_scores": [
            {"chunk_id": f"gdpr-{cid}", "jurisdiction": "GDPR", "level": level, "score": score, "factors": []}
            for cid, _, _, level, score in passages
        ],
        "citation_ids_used": ["C0"],
        "response_time": 0.01,
        "meta": {"passages_found": 3},
    }


def _login(client):
    return client.post(
        "/demo/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        follow_redirects=False,
    )


def _run_query(client, monkeypatch) -> str:
    monkeypatch.setattr("services.demo_service.run_legal_query", _fake_legal_query)
    assert _login(client).status_code == 303
    res = client.post(
        "/demo/query",
        data={"question": "What are the breach notification obligations?", "regulation": "GDPR"},
        follow_redirects=False,
    )
    assert res.status_code == 303, res.text
    assert re.fullmatch(r"/demo/results/\d+", res.headers["location"])
    return res.headers["location"]


def test_login_sets_httponly_cookie(client):
    res = _login(client)
    assert res.status_code == 303
    assert res.headers["location"] == "/demo/query"
    cookie = res.headers["set-cookie"].lower()
    assert "lexai_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/demo/query").status_code == 200


def test_login_rejects_wrong_password(client):
    res = client.post("/demo/login", data={"email": DEMO_EMAIL, "password": "wrong"}, follow_redirects=False)
    assert res.status_code == 401
    assert "Invalid email or password" in res.text
    assert "set-cookie" not in res.headers


def test_protected_pages_redirect_to_login(client):
    for path in ("/demo/query", "/demo/results/1", "/demo/results/1/pdf"):
        res = client.get(path, follow_redirects=False)
        assert res.status_code == 303, path
        assert res.headers["location"] == "/demo/login"


def test_logout_clears_session(client):
    _login(client)
    client.post("/demo/logout", follow_redirects=False)
    assert client.get("/demo/query", follow_redirects=False).status_code == 303


def test_query_shows_risk_score_and_filtered_citations(client, monkeypatch):
    page = client.get(_run_query(client, monkeypatch))
    assert page.status_code == 200
    # Peak risk among hits above the threshold: 0.6 -> 60 / HIGH (the 0.9 passage is below 0.5 relevance).
    assert re.search(r'risk-number">60<', page.text)
    assert "HIGH RISK" in page.text
    assert page.text.count('class="cite-head"') == 2
    assert "Article 99" not in page.text
    assert "Notify the supervisory authority within 72 hours" in page.text


def test_pdf_report_is_valid_pdf(client, monkeypatch):
    res = client.get(_run_query(client, monkeypatch) + "/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
    assert res.content.rstrip().endswith(b"%%EOF")


def test_query_rejects_unknown_regulation(client):
    _login(client)
    res = client.post("/demo/query", data={"question": "Valid question?", "regulation": "HIPAA"})
    assert res.status_code == 400
    assert "choose a regulation" in res.text
