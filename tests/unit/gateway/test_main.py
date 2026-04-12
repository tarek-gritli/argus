import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_ping(patch_gateway_deps):
    """GET /ping returns 200 with pong message."""
    app, _, _ = patch_gateway_deps
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


@pytest.mark.asyncio
async def test_gateway_router_registration(patch_gateway_deps):
    """Gateway includes webhook router with correct prefix."""
    app, _, _ = patch_gateway_deps
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={"X-Hub-Signature-256": "sha256=invalid"},
            json={"action": "opened"},
        )
        assert response.status_code != 404
