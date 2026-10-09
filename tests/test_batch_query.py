"""Batch query: score normalization, thresholding, and POST /query/batch."""

import pytest

from services.batch_service import flatten_query_result, normalize_similarity


def _fake_result(question: str, sims: list[float]) -> dict:
    return {
        "question": question,
        "answer": "Consent is required [C0].",
        "citations": [
            {
                "citation_id": f"C{i}",
                "jurisdiction": "GDPR",
                "source_label": "GDPR Art. 6",
                "heading": f"Article {i}",
                "excerpt": "Processing shall be lawful only if ...",
                "similarity": s,
            }
            for i, s in enumerate(sims)
        ],
        "risk_scores": [
            {"chunk_id": f"gdpr-{i}", "jurisdiction": "GDPR", "level": "medium", "score": 0.3, "factors": []}
            for i in range(len(sims))
        ],
        "response_time": 0.01,
    }


def _register(client, email: str):
    res = client.post(
        "/auth/register",
        json={"name": "Batch User", "email": email, "password": "Testpass1"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.parametrize(
    ("cosine", "mode", "expected"),
    [
        (0.7, "clip", 0.7),
        (-0.3, "clip", 0.0),
        (1.2, "clip", 1.0),
        (0.0, "shift", 0.5),
        (-1.0, "shift", 0.0),
        (0.6, "shift", 0.8),
    ],
)
def test_normalize_similarity(cosine, mode, expected):
    assert normalize_similarity(cosine, mode) == pytest.approx(expected)


def test_normalize_similarity_rejects_unknown_mode():
    with pytest.raises(ValueError):
        normalize_similarity(0.5, "distance")


def test_flatten_marks_hits_strictly_above_threshold():
    rows = flatten_query_result(_fake_result("q", [0.8, 0.5, 0.3]), threshold=0.5)
    assert [r["above_threshold"] for r in rows] == [True, False, False]
    assert rows[0]["chunk_id"] == "gdpr-0"
    assert rows[0]["risk_level"] == "medium"
    assert rows[0]["document"] == "GDPR Art. 6"


def test_batch_endpoint_applies_threshold(client, monkeypatch):
    sims = {"first question": [0.9, 0.6, 0.4], "second question": [0.45]}
    monkeypatch.setattr(
        "services.batch_service.run_legal_query",
        lambda db, engine, *, question, **kw: _fake_result(question, sims[question]),
    )
    headers = _register(client, "batch@example.com")

    res = client.post(
        "/query/batch",
        headers=headers,
        json={"queries": ["first question", "second question"], "jurisdictions": ["GDPR"]},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["threshold"] == 0.5
    assert body["total_hits"] == 2
    first, second = body["results"]
    assert first["hit_count"] == 2 and first["retrieved_count"] == 3
    assert first["top_score"] == pytest.approx(0.9)
    assert first["avg_score"] == pytest.approx(0.75)
    assert second["hit_count"] == 0 and second["top_score"] is None

    stricter = client.post(
        "/query/batch",
        headers=headers,
        json={"queries": ["first question"], "threshold": 0.7},
    )
    assert stricter.json()["results"][0]["hit_count"] == 1


def test_batch_endpoint_validates_input(client):
    headers = _register(client, "batch2@example.com")
    assert client.post("/query/batch", headers=headers, json={"queries": []}).status_code == 422
    assert (
        client.post("/query/batch", headers=headers, json={"queries": ["ok query"], "threshold": 1.5}).status_code
        == 422
    )


def test_batch_endpoint_requires_auth(client):
    assert client.post("/query/batch", json={"queries": ["anything"]}).status_code in (401, 403)
