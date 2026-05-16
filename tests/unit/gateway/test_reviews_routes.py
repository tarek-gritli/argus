from unittest.mock import AsyncMock, MagicMock, patch

from api.routes.reviews import _get_org_id, router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(org_id: str = "org-1"):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/reviews")
    app.dependency_overrides[_get_org_id] = lambda: org_id
    return app


def _mock_review(review_id="rev-1", pr_number=42, status="completed"):
    r = MagicMock()
    r.id = review_id
    r.pr_number = pr_number
    r.head_sha = "abc123"
    r.status = status
    r.created_at = MagicMock()
    r.created_at.isoformat.return_value = "2026-01-01T00:00:00"
    r.completed_at = MagicMock()
    r.completed_at.isoformat.return_value = "2026-01-01T00:01:00"
    return r


def _mock_finding(finding_id="f-1", review_id="rev-1"):
    f = MagicMock()
    f.id = finding_id
    f.review_id = review_id
    f.agent = "security"
    f.severity = "high"
    f.file = "src/auth.py"
    f.line_start = 10
    f.line_end = 15
    f.title = "SQL Injection"
    f.description = "Bad input."
    f.suggestion = "Use parameterized queries."
    f.confidence = 0.95
    f.is_accepted = None
    return f


def _patch_session(mock_db):
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_ctx


def test_list_reviews_returns_200():
    mock_db = AsyncMock()
    reviews = [_mock_review()]
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = reviews
    mock_db.execute = AsyncMock(return_value=execute_result)

    with patch("api.routes.reviews.session_context", return_value=_patch_session(mock_db)):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/reviews")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "rev-1"
    assert data[0]["pr_number"] == 42


def test_list_reviews_empty():
    mock_db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=execute_result)

    with patch("api.routes.reviews.session_context", return_value=_patch_session(mock_db)):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/reviews")

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_review_found():
    mock_db = AsyncMock()
    review = _mock_review()
    findings = [_mock_finding()]

    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=review)),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=findings)))),
        ]
    )

    with patch("api.routes.reviews.session_context", return_value=_patch_session(mock_db)):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/reviews/rev-1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "rev-1"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["title"] == "SQL Injection"


def test_get_review_not_found():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch("api.routes.reviews.session_context", return_value=_patch_session(mock_db)):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/reviews/nonexistent")

    assert resp.status_code == 404


def test_accept_finding():
    mock_db = AsyncMock()
    review = _mock_review()
    finding = _mock_finding()

    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=review)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=finding)),
        ]
    )

    with patch("api.routes.reviews.session_context", return_value=_patch_session(mock_db)):
        client = TestClient(_make_app())
        resp = client.post("/api/v1/reviews/rev-1/findings/f-1/accept")

    assert resp.status_code == 200
    assert finding.is_accepted is True
    mock_db.commit.assert_called_once()


def test_reject_finding():
    mock_db = AsyncMock()
    review = _mock_review()
    finding = _mock_finding()

    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=review)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=finding)),
        ]
    )

    with patch("api.routes.reviews.session_context", return_value=_patch_session(mock_db)):
        client = TestClient(_make_app())
        resp = client.post("/api/v1/reviews/rev-1/findings/f-1/reject")

    assert resp.status_code == 200
    assert finding.is_accepted is False
