from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from integrations.github import PullRequestPayload
from orchestrator.graph import run_review
from pydantic import BaseModel

router = APIRouter()


class LocalReviewRequest(BaseModel):
    diff: str
    files: list[str] | None = None


class _FakeFile:
    def __init__(self, filename: str, patch: str = "") -> None:
        self.filename = filename
        self.patch = patch


def _make_fake_payload() -> PullRequestPayload:
    return PullRequestPayload(
        action="opened",
        repo_full_name="local/local",
        pr_number=0,
        head_sha="local",
        base_sha="local",
        installation_id=0,
    )


@router.post("")
async def local_review(body: LocalReviewRequest, request: Request):
    if body.files:
        files: list[Any] = [_FakeFile(f) for f in body.files]
    else:
        filenames = [line[6:] for line in body.diff.splitlines() if line.startswith("+++ b/")]
        files = [_FakeFile(f) for f in filenames] if filenames else [_FakeFile("unknown")]

    findings = run_review(
        files=files,
        diff=body.diff,
        pr_payload=_make_fake_payload(),
    )
    return {"findings": [f.model_dump() for f in findings]}
