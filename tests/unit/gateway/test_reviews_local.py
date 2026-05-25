from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from shared.schemas import FindingSchema

_SAMPLE_FINDING = FindingSchema(
    agent="security",
    severity="high",
    file="src/auth.py",
    line_start=10,
    line_end=15,
    title="SQL Injection",
    description="User input not sanitized.",
    suggestion="Use parameterized queries.",
    confidence=0.95,
)


def _make_app():
    from api.routes.reviews_local import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/reviews/local")

    @app.middleware("http")
    async def inject_org(request, call_next):
        request.state.org_id = "org-123"
        return await call_next(request)

    return app


def test_local_review_returns_findings():
    app = _make_app()
    client = TestClient(app)
    with patch("api.routes.reviews_local.run_review", return_value=[_SAMPLE_FINDING]):
        resp = client.post("/api/v1/reviews/local", json={"diff": "+ some code"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["findings"]) == 1
    assert data["findings"][0]["title"] == "SQL Injection"


def test_local_review_empty_diff_returns_empty():
    app = _make_app()
    client = TestClient(app)
    with patch("api.routes.reviews_local.run_review", return_value=[]):
        resp = client.post("/api/v1/reviews/local", json={"diff": ""})
    assert resp.status_code == 200
    assert resp.json()["findings"] == []


def test_local_review_with_files_filter():
    app = _make_app()
    client = TestClient(app)
    with patch("api.routes.reviews_local.run_review", return_value=[_SAMPLE_FINDING]) as mock_review:
        resp = client.post(
            "/api/v1/reviews/local",
            json={"diff": "+ some code", "files": ["src/auth.py"]},
        )
    assert resp.status_code == 200
    call_kwargs = mock_review.call_args.kwargs
    filenames = [f.filename for f in call_kwargs["files"]]
    assert filenames == ["src/auth.py"]
