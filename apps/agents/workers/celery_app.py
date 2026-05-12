from celery import Celery
from shared.config import get_settings
from shared.queue.tasks import REVIEW_PR_TASK_NAME

settings = get_settings()

celery_app = Celery(
    "agents",
    broker=settings.celery_broker_url,
    backend=None,
)

celery_app.conf.update(
    worker_pool="threads",
    worker_concurrency=3,
)


@celery_app.task(name=REVIEW_PR_TASK_NAME)
def review_pr(payload: dict) -> None:
    """Receive PR review task from gateway, invoke coordinator."""
    from orchestrator.coordinator import run

    run(payload)
