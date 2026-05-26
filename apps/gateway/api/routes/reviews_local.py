from __future__ import annotations

import json
import secrets

from celery import Celery
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from shared.config import get_settings
from shared.queue.tasks import REVIEW_LOCAL_TASK_NAME

router = APIRouter()

_RESULT_TTL = 300


def _get_celery() -> Celery:
    return Celery(broker=get_settings().celery_broker_url)


class LocalReviewRequest(BaseModel):
    diff: str
    files: list[str] | None = None


@router.post("", status_code=202)
async def submit_local_review(body: LocalReviewRequest, request: Request):
    if not body.diff.strip():
        return Response(status_code=400, content="diff is empty")

    job_id = secrets.token_urlsafe(16)
    _get_celery().send_task(
        REVIEW_LOCAL_TASK_NAME,
        kwargs={"job_id": job_id, "diff": body.diff, "files": body.files},
    )
    return {
        "job_id": job_id,
        "stream_url": f"/api/v1/reviews/local/{job_id}/stream",
        "status_url": f"/api/v1/reviews/local/{job_id}",
    }


@router.get("/{job_id}")
async def poll_local_review(job_id: str, request: Request):
    result = await request.app.state.redis.get(f"local_review:{job_id}:result")
    if result is None:
        return Response(
            status_code=202,
            content=json.dumps({"status": "pending"}),
            media_type="application/json",
        )
    findings = json.loads(result)
    return {"status": "done", "findings": findings}


@router.get("/{job_id}/stream")
async def stream_local_review(job_id: str, request: Request):
    async def event_generator():
        pubsub = request.app.state.redis.pubsub()
        await pubsub.subscribe(f"local_review:{job_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = json.loads(message["data"])
                event = payload["event"]
                data = json.dumps(payload["data"])
                yield f"event: {event}\ndata: {data}\n\n"
                if event in ("done", "error"):
                    break
        finally:
            await pubsub.unsubscribe(f"local_review:{job_id}")
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
