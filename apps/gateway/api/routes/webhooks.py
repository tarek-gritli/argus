import json
import logging

from fastapi import APIRouter, Depends, Request, Response
from integrations.github import PullRequestPayload, validate_signature
from org_resolver import get_or_create_org
from shared.config import Settings, get_settings
from shared.db import session_context
from shared.queue.tasks import INDEX_REPO_TASK_NAME, REVIEW_PR_TASK_NAME

router = APIRouter()
logger = logging.getLogger(__name__)

DELIVERY_TTL = 86400


async def _get_repo_id(installation_id: int | None, repo_full_name: str | None) -> str | None:
    if not installation_id or not repo_full_name:
        return None
    try:
        from shared.models import Repo
        from sqlalchemy import select

        async with session_context() as session:
            repo = (
                await session.execute(
                    select(Repo).where(
                        Repo.installation_id == installation_id,
                        Repo.full_name == repo_full_name,
                    )
                )
            ).scalar_one_or_none()
            return repo.id if repo else None
    except Exception:
        logger.warning("_get_repo_id failed", exc_info=True)
        return None


@router.post("/github")
async def github_webhook(request: Request, settings: Settings = Depends(get_settings)) -> Response:
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not validate_signature(payload, signature, settings.github_webhook_secret):
        return Response(status_code=403, content="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")

    if event == "push":
        body = json.loads(payload)
        ref = body.get("ref", "")
        repo_data = body.get("repository", {})
        default_branch = repo_data.get("default_branch", "main")

        if ref != f"refs/heads/{default_branch}":
            return Response(status_code=200)

        installation_id = body.get("installation", {}).get("id")
        repo_full_name = repo_data.get("full_name")
        ref_name = ref.removeprefix("refs/heads/")

        repo_id = await _get_repo_id(installation_id, repo_full_name)
        if repo_id:
            celery_app = request.app.state.celery
            celery_app.send_task(
                INDEX_REPO_TASK_NAME,
                kwargs={
                    "repo_id": repo_id,
                    "installation_id": installation_id,
                    "repo_full_name": repo_full_name,
                    "ref": ref_name,
                },
            )
        return Response(status_code=200)

    if event != "pull_request":
        return Response(status_code=200)

    body = json.loads(payload)

    action = body.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return Response(status_code=200)

    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not delivery_id:
        return Response(status_code=400)

    redis_client = request.app.state.redis

    acquired = await redis_client.set(delivery_id, "1", ex=DELIVERY_TTL, nx=True)

    if not acquired:
        return Response(status_code=200)

    repo = body.get("repository", {})
    pr = body.get("pull_request", {})
    installation = body.get("installation", {})

    try:
        extracted_payload = PullRequestPayload(
            repo_full_name=repo["full_name"],
            pr_number=pr["number"],
            head_sha=pr["head"]["sha"],
            base_sha=pr["base"]["sha"],
            installation_id=installation["id"],
            action=action,
        )
    except (KeyError, ValueError) as e:
        await redis_client.delete(delivery_id)
        return Response(status_code=400, content=f"Malformed payload: {e}")

    try:
        async with session_context() as session:
            org_id = await get_or_create_org(session, extracted_payload.installation_id, extracted_payload.repo_full_name)
    except Exception:
        await redis_client.delete(delivery_id)
        return Response(status_code=503, content="Org resolution failed")

    payload_dict = extracted_payload.model_dump()
    payload_dict["org_id"] = org_id

    celery_app = request.app.state.celery
    try:
        celery_app.send_task(REVIEW_PR_TASK_NAME, args=[payload_dict])
    except Exception:
        await redis_client.delete(delivery_id)
        return Response(status_code=503, content="Queue unavailable")

    return Response(status_code=200)
