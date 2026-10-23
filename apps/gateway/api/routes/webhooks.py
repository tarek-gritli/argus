import json
import logging

from fastapi import APIRouter, Depends, Request, Response
from integrations.github import PullRequestPayload, validate_signature
from integrations.gitlab import MergeRequestPayload, validate_gitlab_signature, validate_gitlab_token
from org_resolver import ensure_gitlab_repo, get_or_create_org
from shared.config import Settings, get_settings
from shared.crypto import decrypt
from shared.db import session_context
from shared.models.org_integration import OrgIntegration
from shared.queue.tasks import INDEX_REPO_TASK_NAME, REVIEW_PR_TASK_NAME
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter()

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
            logger.info("push ignored: ref=%s is not default branch (%s)", ref, default_branch)
            return Response(status_code=200)

        installation_id = body.get("installation", {}).get("id")
        repo_full_name = repo_data.get("full_name")
        ref_name = ref.removeprefix("refs/heads/")

        repo_id = await _get_repo_id(installation_id, repo_full_name)
        if not repo_id:
            logger.info("push ignored: repo %s not found in DB (not yet installed?)", repo_full_name)
            return Response(status_code=200)

        redis_client = request.app.state.redis
        latest_key = f"index:latest:{repo_id}"
        scheduled_key = f"index:scheduled:{repo_id}"
        try:
            await redis_client.set(latest_key, ref_name, ex=600)
            scheduled = await redis_client.set(scheduled_key, "1", ex=300, nx=True)
        except Exception:
            logger.warning(
                "Redis unavailable for repo_id=%s ref=%s installation_id=%s — enqueuing with ref fallback",
                repo_id,
                ref_name,
                installation_id,
                exc_info=True,
            )
            scheduled = True
        if scheduled:
            celery_app = request.app.state.celery
            try:
                celery_app.send_task(
                    INDEX_REPO_TASK_NAME,
                    kwargs={
                        "repo_id": repo_id,
                        "installation_id": installation_id,
                        "repo_full_name": repo_full_name,
                        "ref": ref_name,
                    },
                    countdown=300,
                )
                logger.info("index task scheduled: repo=%s ref=%s (5 min delay)", repo_full_name, ref_name)
            except Exception:
                try:
                    await redis_client.delete(scheduled_key)
                except Exception:
                    logger.warning("Failed to clean up scheduled_key for repo_id=%s", repo_id, exc_info=True)
                logger.warning("Failed to enqueue %s for repo_id=%s", INDEX_REPO_TASK_NAME, repo_id, exc_info=True)
        else:
            logger.info("index already scheduled for repo=%s — debounced", repo_full_name)
        return Response(status_code=200)

    if event != "pull_request":
        logger.debug("event=%s ignored", event)
        return Response(status_code=200)

    body = json.loads(payload)

    action = body.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        logger.debug("pull_request action=%s ignored", action)
        return Response(status_code=200)

    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not delivery_id:
        return Response(status_code=400)

    redis_client = request.app.state.redis

    acquired = await redis_client.set(delivery_id, "1", ex=DELIVERY_TTL, nx=True)

    if not acquired:
        logger.info("delivery %s already processed — skipping duplicate", delivery_id)
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
    payload_dict["platform"] = "github"

    celery_app = request.app.state.celery
    try:
        celery_app.send_task(REVIEW_PR_TASK_NAME, args=[payload_dict])
        logger.info(
            "review task enqueued: repo=%s PR#%d action=%s org_id=%s",
            extracted_payload.repo_full_name,
            extracted_payload.pr_number,
            action,
            org_id,
        )
    except Exception:
        await redis_client.delete(delivery_id)
        return Response(status_code=503, content="Queue unavailable")

    return Response(status_code=200)


@router.post("/gitlab/{integration_id}")
async def gitlab_webhook(integration_id: str, request: Request) -> Response:
    """Merge-request webhook for one org's GitLab integration (gitlab.com or self-hosted).

    Each integration has its own URL and secrets, so the org is known from the path and
    nothing global is shared between tenants.
    """
    payload_bytes = await request.body()

    async with session_context() as session:
        integration = (
            await session.execute(
                select(OrgIntegration).where(
                    OrgIntegration.id == integration_id,
                    OrgIntegration.kind == "gitlab",
                    OrgIntegration.enabled.is_(True),
                )
            )
        ).scalar_one_or_none()
    if integration is None:
        return Response(status_code=403, content="Invalid signature")
    cfg = integration.config

    # A configured signing token must be honored — never fall back to the weaker secret header.
    if cfg.get("signing_token"):
        authentic = validate_gitlab_signature(
            payload_bytes,
            request.headers.get("webhook-signature", ""),
            request.headers.get("webhook-id", ""),
            request.headers.get("webhook-timestamp", ""),
            decrypt(cfg["signing_token"]),
        )
    else:
        secret = decrypt(cfg["webhook_secret"]) if cfg.get("webhook_secret") else ""
        authentic = validate_gitlab_token(request.headers.get("X-Gitlab-Token", ""), secret)
    if not authentic:
        logger.warning("Rejected GitLab webhook for integration %s: bad signature/token", integration_id)
        return Response(status_code=403, content="Invalid signature")

    if request.headers.get("X-Gitlab-Event", "") != "Merge Request Hook":
        return Response(status_code=200, content="Event ignored")

    try:
        body = json.loads(payload_bytes)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON payload")

    attrs = body.get("object_attributes", {})
    # Normalize GitLab actions to the ones the GitHub path uses
    action = {"open": "opened", "update": "synchronize", "reopen": "reopened"}.get(attrs.get("action", ""), "")
    if not action:
        return Response(status_code=200, content="Action ignored")
    # "update" also fires for title/label edits; only a new head commit is worth a review
    if action == "synchronize" and "oldrev" not in attrs:
        return Response(status_code=200, content="No new commits")

    project = body.get("project", {})
    try:
        extracted = MergeRequestPayload(
            project_id=project["id"],
            project_path=project["path_with_namespace"],
            mr_iid=attrs["iid"],
            head_sha=attrs.get("last_commit", {}).get("id", ""),
            base_sha=attrs.get("target", {}).get("commit", {}).get("id", "") if isinstance(attrs.get("target"), dict) else "",
            action=action,
            org_id=integration.org_id,
            integration_id=integration.id,
        )
    except (KeyError, ValueError) as e:
        return Response(status_code=400, content=f"Malformed payload: {e}")
    if not extracted.head_sha:
        return Response(status_code=400, content="Malformed payload: missing head commit")

    # Idempotent on content, not on a (possibly unsigned) delivery header: GitLab retries
    # carry the same MR + head commit.
    redis_client = request.app.state.redis
    dedupe_key = f"gitlab:{integration.id}:{extracted.project_id}:{extracted.mr_iid}:{extracted.head_sha}"
    if not await redis_client.set(dedupe_key, "1", ex=DELIVERY_TTL, nx=True):
        logger.info("duplicate GitLab delivery %s — skipping", dedupe_key)
        return Response(status_code=200, content="Duplicate event bypassed")

    try:
        async with session_context() as session:
            await ensure_gitlab_repo(session, integration.org_id, extracted.project_path)
    except Exception:
        await redis_client.delete(dedupe_key)
        return Response(status_code=503, content="Repo resolution failed")

    payload_dict = extracted.model_dump()
    payload_dict["platform"] = "gitlab"
    try:
        request.app.state.celery.send_task(REVIEW_PR_TASK_NAME, args=[payload_dict])
        logger.info("review task enqueued: gitlab %s !%d org_id=%s", extracted.project_path, extracted.mr_iid, integration.org_id)
    except Exception:
        logger.exception("Celery unreachable for GitLab MR")
        await redis_client.delete(dedupe_key)
        return Response(status_code=503, content="Queue unavailable")

    return Response(status_code=200, content="Webhook accepted")
