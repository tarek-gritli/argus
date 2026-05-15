from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from middleware.auth import AuthMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/protected")
    def protected(request: Request):
        return {"org_id": request.state.org_id}

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_exempt_path_no_token_needed():
    with patch("middleware.auth.get_settings") as mock:
        mock.return_value.jwt_secret_key = "test-secret-key-32-bytes-padding!"
        client = TestClient(_make_app())
        resp = client.get("/ping")
        assert resp.status_code == 200


def test_protected_without_token_returns_401():
    with patch("middleware.auth.get_settings") as mock:
        mock.return_value.jwt_secret_key = "test-secret-key-32-bytes-padding!"
        client = TestClient(_make_app())
        resp = client.get("/protected")
        assert resp.status_code == 401


def test_protected_with_valid_token():
    import jwt as _jwt

    with patch("middleware.auth.get_settings") as mock:
        mock.return_value.jwt_secret_key = "test-secret-key-32-bytes-padding!"
        token = _jwt.encode(
            {"sub": "u1", "oid": "o1", "role": "owner", "exp": 9999999999},
            "test-secret-key-32-bytes-padding!",
            algorithm="HS256",
        )
        client = TestClient(_make_app())
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
