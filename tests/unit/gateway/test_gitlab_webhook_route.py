import base64
import hashlib
import hmac
import json
import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from shared.crypto import encrypt
from shared.models.org_integration import OrgIntegration

URL = "/api/v1/webhooks/gitlab/int-1"
SECRET = "hook-secret"

MR_BODY = {
    "object_attributes": {
        "action": "open",
        "iid": 3,
        "last_commit": {"id": "head123"},
        "target": {"commit": {"id": "base456"}},
    },
    "project": {"id": 7, "path_with_namespace": "group/proj"},
}


def _integration(**extra):
    config = {"base_url": "https://gitlab.com", "access_token": encrypt("glpat"), "webhook_secret": encrypt(SECRET), **extra}
    return OrgIntegration(id="int-1", org_id="org-1", kind="gitlab", config=config)


@contextmanager
def _db(integration):
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=integration)))
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    with (
        patch("api.routes.webhooks.session_context", return_value=ctx),
        patch("api.routes.webhooks.ensure_gitlab_repo", new=AsyncMock()) as ensure,
    ):
        yield ensure


async def _post(app, body=MR_BODY, headers=None):
    h = {"X-Gitlab-Event": "Merge Request Hook", "X-Gitlab-Token": SECRET, **(headers or {})}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(URL, content=json.dumps(body), headers=h)


@pytest.mark.asyncio
async def test_unknown_integration_is_rejected(patch_gateway_deps):
    app, _, celery = patch_gateway_deps
    with _db(None):
        resp = await _post(app)
    assert resp.status_code == 403
    celery.send_task.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["wrong", ""])
async def test_bad_secret_token_is_rejected(patch_gateway_deps, token):
    app, _, celery = patch_gateway_deps
    with _db(_integration()):
        resp = await _post(app, headers={"X-Gitlab-Token": token})
    assert resp.status_code == 403
    celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_opened_mr_enqueues_review_scoped_to_integration_org(patch_gateway_deps):
    app, _, celery = patch_gateway_deps
    with _db(_integration()) as ensure_repo:
        resp = await _post(app)

    assert resp.status_code == 200
    ensure_repo.assert_awaited_once()
    assert ensure_repo.await_args.args[1:] == ("org-1", "group/proj")
    payload = celery.send_task.call_args.kwargs["args"][0]
    assert payload == {
        "project_id": 7,
        "project_path": "group/proj",
        "mr_iid": 3,
        "head_sha": "head123",
        "base_sha": "base456",
        "action": "opened",
        "org_id": "org-1",
        "integration_id": "int-1",
        "platform": "gitlab",
    }


@pytest.mark.asyncio
async def test_other_events_are_ignored(patch_gateway_deps):
    app, _, celery = patch_gateway_deps
    with _db(_integration()):
        resp = await _post(app, headers={"X-Gitlab-Event": "Push Hook"})
    assert resp.status_code == 200
    celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_update_without_new_commits_is_ignored_but_with_oldrev_is_reviewed(patch_gateway_deps):
    app, _, celery = patch_gateway_deps
    update = json.loads(json.dumps(MR_BODY))
    update["object_attributes"]["action"] = "update"
    with _db(_integration()):
        await _post(app, body=update)
    celery.send_task.assert_not_called()

    update["object_attributes"]["oldrev"] = "old"
    with _db(_integration()):
        await _post(app, body=update)
    celery.send_task.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_delivery_is_skipped(patch_gateway_deps):
    app, redis, celery = patch_gateway_deps
    redis.set.return_value = False
    with _db(_integration()):
        resp = await _post(app)
    assert resp.status_code == 200
    celery.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_queue_failure_releases_dedupe_key(patch_gateway_deps):
    app, redis, celery = patch_gateway_deps
    celery.send_task.side_effect = RuntimeError("down")
    with _db(_integration()):
        resp = await _post(app)
    assert resp.status_code == 503
    redis.delete.assert_awaited_once()


def _sign(body: bytes, webhook_id: str, key: bytes):
    ts = str(int(time.time()))
    digest = hmac.new(key, f"{webhook_id}.{ts}.".encode() + body, hashlib.sha256).digest()
    return {"webhook-id": webhook_id, "webhook-timestamp": ts, "webhook-signature": f"v1,{base64.b64encode(digest).decode()}"}


@pytest.mark.asyncio
async def test_signing_token_is_enforced_and_secret_header_cannot_downgrade(patch_gateway_deps):
    app, _, celery = patch_gateway_deps
    key = b"signing-key"
    integration = _integration(signing_token=encrypt("whsec_" + base64.b64encode(key).decode()))

    with _db(integration):  # right X-Gitlab-Token but no signature -> still rejected
        assert (await _post(app)).status_code == 403
    celery.send_task.assert_not_called()

    body = json.dumps(MR_BODY).encode()
    with _db(integration):
        resp = await _post(app, headers={**_sign(body, "wh-1", key), "X-Gitlab-Token": ""})
    assert resp.status_code == 200
    celery.send_task.assert_called_once()
