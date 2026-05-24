import json
import logging

from fastapi import APIRouter, Depends, Request, Response
from integrations.github import PullRequestPayload, validate_signature
from integrations.gitlab import MergeRequestPayload, validate_gitlab_signature
from shared.config import Settings, get_settings
from shared.queue.tasks import REVIEW_PR_TASK_NAME

logger = logging.getLogger(__name__)
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

    celery_app = request.app.state.celery
    try:
        payload_dict = extracted_payload.model_dump()
        payload_dict["platform"] = "github"
        celery_app.send_task(REVIEW_PR_TASK_NAME, args=[payload_dict])
    except Exception:
        await redis_client.delete(delivery_id)
        return Response(status_code=503, content="Queue unavailable")

    return Response(status_code=200)


@router.post("/gitlab")
async def gitlab_webhook(request: Request, settings: Settings = Depends(get_settings)) -> Response:
    # 1. Read body once to prevent stream exhaustion
    payload_bytes = await request.body()

    # 2. Extract Standard Webhook validation headers
    signature = request.headers.get("webhook-signature", "")
    webhook_id = request.headers.get("webhook-id", "")
    timestamp = request.headers.get("webhook-timestamp", "")
    signing_token = settings.gitlab_signing_token

    # Validate cryptographic signature
    if not validate_gitlab_signature(payload_bytes, signature, webhook_id, timestamp, signing_token):
        logger.warning(f"Rejected webhook delivery with invalid signature. ID: {webhook_id}")
        return Response(status_code=403, content="Invalid signature")

    # 3. Filter by Event Type
    event = request.headers.get("X-Gitlab-Event", "")
    if event != "Merge Request Hook":
        return Response(status_code=200, content="Event ignored")

    # 4. Parse JSON Payload safely
    try:
        body = json.loads(payload_bytes)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON payload")

    object_attributes = body.get("object_attributes", {})
    action = object_attributes.get("action", "")

    # Normalize GitLab events to match Argus' engine structure
    action_mapping = {"open": "opened", "update": "synchronize", "reopen": "reopened"}
    action = action_mapping.get(action, action)

    if action not in ("opened", "synchronize", "reopened"):
        return Response(status_code=200, content=f"Action '{action}' bypassed")

    # 5. Idempotency Check using Redis
    delivery_id = request.headers.get("X-Gitlab-Event-UUID") or webhook_id
    if not delivery_id:
        return Response(status_code=400, content="Missing unique delivery identifier")

    redis_client = request.app.state.redis
    acquired = await redis_client.set(f"webhook:idempotency:{delivery_id}", "1", ex=DELIVERY_TTL, nx=True)
    if not acquired:
        logger.info(f"Duplicate delivery detected for ID {delivery_id}. Skiped processing.")
        return Response(status_code=200, content="Duplicate event bypassed")

    # 6. Extract target tracking metrics
    project = body.get("project", {})
    try:
        extracted_payload = MergeRequestPayload(
            project_id=project["id"],
            mr_iid=object_attributes["iid"],
            head_sha=object_attributes.get("last_commit", {}).get("id", ""),
            base_sha=object_attributes.get("target", {}).get("commit", {}).get("id", ""),
            action=action,
        )
    except (KeyError, ValueError) as e:
        logger.error(f"Failed parsing MergeRequestPayload validation schema: {e}")
        await redis_client.delete(f"webhook:idempotency:{delivery_id}")
        return Response(status_code=400, content=f"Malformed payload: {e}")

    # 7. Disperse task handling to Celery workers
    celery_app = request.app.state.celery
    try:
        payload_dict = extracted_payload.model_dump()
        payload_dict["platform"] = "gitlab"
        celery_app.send_task(REVIEW_PR_TASK_NAME, args=[payload_dict])
    except Exception as e:
        logger.critical(f"Celery cluster unreachable. Evicting cache lock key. Error: {e}")
        await redis_client.delete(f"webhook:idempotency:{delivery_id}")
        return Response(status_code=503, content="Worker queue unavailable")

    return Response(status_code=200, content="Webhook accepted and scheduled")
