import hashlib
import hmac
import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


def generate_signature(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


VALID_PR_PAYLOAD = {
    "action": "opened",
    "pull_request": {
        "number": 123,
        "head": {"sha": "abc123def456"},
        "base": {"sha": "base789"},
    },
    "repository": {"full_name": "owner/repo"},
    "installation": {"id": 999},
}

VALID_PR_PAYLOAD_SYNC = {
    "action": "synchronize",
    "pull_request": {
        "number": 123,
        "head": {"sha": "abc123def456new"},
        "base": {"sha": "base789"},
    },
    "repository": {"full_name": "owner/repo"},
    "installation": {"id": 999},
}

VALID_PR_PAYLOAD_REOPEN = {
    "action": "reopened",
    "pull_request": {
        "number": 123,
        "head": {"sha": "abc123def456"},
        "base": {"sha": "base789"},
    },
    "repository": {"full_name": "owner/repo"},
    "installation": {"id": 999},
}


@pytest.mark.asyncio
async def test_github_webhook_invalid_signature(patch_gateway_deps):
    """Invalid HMAC-SHA256 signature → 403 Forbidden."""
    app, _, _ = patch_gateway_deps
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={"X-Hub-Signature-256": "sha256=invalid"},
            json={"action": "opened"},
        )
    assert response.status_code == 403
    assert response.text == "Invalid signature"


@pytest.mark.asyncio
async def test_github_webhook_valid_pr_opened(patch_gateway_deps):
    """Valid PR opened event → enqueues task, returns 200."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = True  # New delivery_id (not duplicate)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-123",
            },
            content=payload,
        )

    assert response.status_code == 200
    mock_redis.set.assert_called_once()
    mock_celery.send_task.assert_called_once()
    call_args = mock_celery.send_task.call_args
    assert call_args[0][0] == "review_pr"
    assert call_args[1]["args"][0]["repo_full_name"] == "owner/repo"
    assert call_args[1]["args"][0]["pr_number"] == 123


@pytest.mark.asyncio
async def test_github_webhook_valid_pr_synchronize(patch_gateway_deps):
    """Valid PR synchronize event → enqueues task, returns 200."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD_SYNC).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-456",
            },
            content=payload,
        )

    assert response.status_code == 200
    mock_celery.send_task.assert_called_once()


@pytest.mark.asyncio
async def test_github_webhook_valid_pr_reopened(patch_gateway_deps):
    """Valid PR reopened event → enqueues task, returns 200."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD_REOPEN).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set = AsyncMock(return_value=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-789",
            },
            content=payload,
        )

    assert response.status_code == 200
    mock_celery.send_task.assert_called_once()


@pytest.mark.asyncio
async def test_github_webhook_non_pr_event(patch_gateway_deps):
    """Non-pull_request event (e.g., push) → 200, no task enqueued."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps({"action": "created"}).encode()
    signature = generate_signature(payload, "test-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "push",  # Not pull_request
                "X-GitHub-Delivery": "delivery-push",
            },
            content=payload,
        )

    assert response.status_code == 200
    mock_celery.send_task.assert_not_called()
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_github_webhook_pr_event_wrong_action(patch_gateway_deps):
    """pull_request event with unsupported action (e.g., closed) → 200, no task."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD | {"action": "closed"}).encode()
    signature = generate_signature(payload, "test-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "delivery-closed",
            },
            content=payload,
        )

    assert response.status_code == 200
    mock_celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_github_webhook_duplicate_delivery(patch_gateway_deps):
    """Duplicate X-GitHub-Delivery (already processed) → 200, no task enqueued."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = False  # nx=True failed, already exists

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "duplicate-id",
            },
            content=payload,
        )

    assert response.status_code == 200
    mock_celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_github_webhook_missing_delivery_id(patch_gateway_deps):
    """Missing X-GitHub-Delivery header → 400 Bad Request."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD).encode()
    signature = generate_signature(payload, "test-secret")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                # Missing X-GitHub-Delivery
            },
            content=payload,
        )

    assert response.status_code == 400
    mock_celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_github_webhook_malformed_payload_missing_field(patch_gateway_deps):
    """Malformed payload (missing pr.head.sha) → 400, delivery_id cleaned up."""
    app, mock_redis, mock_celery = patch_gateway_deps
    malformed_payload = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "head": {},  # Missing sha
            "base": {"sha": "base789"},
        },
        "repository": {"full_name": "owner/repo"},
        "installation": {"id": 999},
    }
    payload = json.dumps(malformed_payload).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "malformed-id",
            },
            content=payload,
        )

    assert response.status_code == 400
    mock_redis.delete.assert_called_once_with("malformed-id")
    mock_celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_github_webhook_malformed_payload_missing_repo(patch_gateway_deps):
    """Malformed payload (missing repository) → 400, delivery_id cleaned up."""
    app, mock_redis, mock_celery = patch_gateway_deps
    malformed_payload = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "head": {"sha": "abc123"},
            "base": {"sha": "base789"},
        },
        # Missing repository
        "installation": {"id": 999},
    }
    payload = json.dumps(malformed_payload).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "missing-repo-id",
            },
            content=payload,
        )

    assert response.status_code == 400
    mock_redis.delete.assert_called_once()
    mock_celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_github_webhook_celery_task_failure(patch_gateway_deps):
    """Celery task enqueue fails → 503, delivery_id cleaned up."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = True
    mock_celery.send_task.side_effect = Exception("Celery broker unreachable")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "celery-fail-id",
            },
            content=payload,
        )

    assert response.status_code == 503
    assert "Queue unavailable" in response.text
    mock_redis.delete.assert_called_once_with("celery-fail-id")


@pytest.mark.asyncio
async def test_github_webhook_payload_extraction(patch_gateway_deps):
    """Verify correct payload extraction from complex GitHub webhook."""
    app, mock_redis, mock_celery = patch_gateway_deps
    payload = json.dumps(VALID_PR_PAYLOAD).encode()
    signature = generate_signature(payload, "test-secret")

    mock_redis.set.return_value = True

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/webhooks/github",
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "extraction-test",
            },
            content=payload,
        )

    # Verify Celery received the correct extracted payload
    call_args = mock_celery.send_task.call_args
    task_payload = call_args[1]["args"][0]
    assert task_payload["repo_full_name"] == "owner/repo"
    assert task_payload["pr_number"] == 123
    assert task_payload["head_sha"] == "abc123def456"
    assert task_payload["base_sha"] == "base789"
    assert task_payload["installation_id"] == 999
    assert task_payload["action"] == "opened"
