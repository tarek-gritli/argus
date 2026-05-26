from __future__ import annotations

import json
import logging
from typing import Any

from integrations.github import PullRequestPayload
from specialized.quality import analyze as quality_analyze
from specialized.security import analyze as security_analyze
from specialized.testing import analyze as testing_analyze

logger = logging.getLogger(__name__)

_RESULT_TTL = 300


def _get_redis():
    from workers.connections import get_redis_client

    return get_redis_client()


class _FakeFile:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.patch = ""


def _fake_payload() -> PullRequestPayload:
    return PullRequestPayload(
        action="opened",
        repo_full_name="local/local",
        pr_number=0,
        head_sha="local",
        base_sha="local",
        installation_id=0,
    )


def _publish(redis_client, channel: str, event: str, data: Any) -> None:
    redis_client.publish(channel, json.dumps({"event": event, "data": data}))


def run_local_review(job_id: str, diff: str, files: list[str] | None) -> None:
    redis_client = _get_redis()
    channel = f"local_review:{job_id}"
    result_key = f"local_review:{job_id}:result"
    status_key = f"local_review:{job_id}:status"

    if files:
        file_objects: list[Any] = [_FakeFile(f) for f in files]
    else:
        filenames = [line[6:] for line in diff.splitlines() if line.startswith("+++ b/")]
        file_objects = [_FakeFile(f) for f in filenames] if filenames else [_FakeFile("unknown")]

    pr_payload = _fake_payload()
    all_findings: list[dict] = []

    agents = [
        ("security", security_analyze),
        ("quality", quality_analyze),
        ("testing", testing_analyze),
    ]

    try:
        for agent_name, analyze_fn in agents:
            try:
                findings = analyze_fn(file_objects, diff, pr_payload)
                for finding in findings:
                    dumped = finding.model_dump()
                    all_findings.append(dumped)
                    _publish(redis_client, channel, "finding", dumped)
            except Exception:
                logger.exception("Agent %s failed in local review %s", agent_name, job_id)

        redis_client.setex(result_key, _RESULT_TTL, json.dumps(all_findings))
        redis_client.setex(status_key, _RESULT_TTL, "done")
        _publish(redis_client, channel, "done", {})

    except Exception as exc:
        logger.exception("Local review %s failed", job_id)
        try:
            redis_client.setex(status_key, _RESULT_TTL, "error")
            _publish(redis_client, channel, "error", {"message": str(exc)})
        except Exception:
            logger.exception("Failed to publish error event for local review %s", job_id)
