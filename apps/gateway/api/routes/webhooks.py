import json

from fastapi import APIRouter, Depends, Request, Response
from integrations.github import PullRequestPayload, validate_signature
from org_resolver import get_or_create_org
from shared.config import Settings, get_settings
from shared.db import session_context
from shared.queue.tasks import REVIEW_PR_TASK_NAME

router = APIRouter()

DELIVERY_TTL = 86400


@router.post("/github")
async def github_webhook(request: Request, settings: Settings = Depends(get_settings)) -> Response:
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not validate_signature(payload, signature, settings.github_webhook_secret):
        return Response(status_code=403, content="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
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

    async with session_context() as session:
        org_id = await get_or_create_org(session, extracted_payload.installation_id, extracted_payload.repo_full_name)

    payload_dict = extracted_payload.model_dump()
    payload_dict["org_id"] = org_id

    celery_app = request.app.state.celery
    try:
        celery_app.send_task(REVIEW_PR_TASK_NAME, args=[payload_dict])
    except Exception:
        await redis_client.delete(delivery_id)
        return Response(status_code=503, content="Queue unavailable")

    return Response(status_code=200)
