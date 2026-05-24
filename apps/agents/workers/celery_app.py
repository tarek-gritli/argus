from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from shared.config import get_settings
from shared.queue.tasks import INDEX_REPO_TASK_NAME, REVIEW_PR_TASK_NAME

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


@worker_process_init.connect
def on_worker_init(**_) -> None:
    from workers.connections import init_connections

    init_connections()


@worker_process_shutdown.connect
def on_worker_shutdown(**_) -> None:
    from workers.connections import close_connections

    close_connections()


@celery_app.task(name=REVIEW_PR_TASK_NAME)
def review_pr(payload: dict) -> None:
    """Receive PR review task from gateway, invoke coordinator."""
    from orchestrator.coordinator import run

    run(payload)


@celery_app.task(name=INDEX_REPO_TASK_NAME)
def index_repo(repo_id: str, installation_id: int, repo_full_name: str, ref: str = "main") -> None:
    from workers.index_task import index_repo_task

    index_repo_task(
        repo_id=repo_id,
        installation_id=installation_id,
        repo_full_name=repo_full_name,
        ref=ref,
    )
