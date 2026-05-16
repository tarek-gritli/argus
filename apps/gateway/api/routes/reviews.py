from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from shared.db import session_context
from shared.models import Finding as FindingModel
from shared.models import Review
from sqlalchemy import select

router = APIRouter()


def _get_org_id(request: Request) -> str:
    return request.state.org_id


@router.get("")
async def list_reviews(
    org_id: str = Depends(_get_org_id),
    page: int = 1,
    per_page: int = 20,
):
    offset = (page - 1) * per_page
    async with session_context() as session:
        result = await session.execute(select(Review).where(Review.org_id == org_id).offset(offset).limit(per_page))
        reviews = result.scalars().all()
    return [
        {
            "id": r.id,
            "pr_number": r.pr_number,
            "head_sha": r.head_sha,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in reviews
    ]


@router.get("/{review_id}")
async def get_review(
    review_id: str,
    org_id: str = Depends(_get_org_id),
):
    async with session_context() as session:
        result = await session.execute(select(Review).where(Review.id == review_id, Review.org_id == org_id))
        review = result.scalar_one_or_none()
        if not review:
            raise HTTPException(status_code=404)
        findings_result = await session.execute(select(FindingModel).where(FindingModel.review_id == review_id))
        findings = findings_result.scalars().all()
    return {
        "id": review.id,
        "pr_number": review.pr_number,
        "status": review.status,
        "findings": [
            {
                "id": f.id,
                "agent": f.agent,
                "severity": f.severity,
                "file": f.file,
                "line_start": f.line_start,
                "line_end": f.line_end,
                "title": f.title,
                "description": f.description,
                "suggestion": f.suggestion,
                "confidence": f.confidence,
                "is_accepted": f.is_accepted,
            }
            for f in findings
        ],
    }


@router.get("/{review_id}/findings")
async def list_findings(
    review_id: str,
    org_id: str = Depends(_get_org_id),
    severity: str | None = None,
    agent: str | None = None,
):
    async with session_context() as session:
        result = await session.execute(select(Review).where(Review.id == review_id, Review.org_id == org_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404)

        query = select(FindingModel).where(FindingModel.review_id == review_id)
        if severity:
            query = query.where(FindingModel.severity == severity)
        if agent:
            query = query.where(FindingModel.agent == agent)

        findings_result = await session.execute(query)
        findings = findings_result.scalars().all()
    return [{"id": f.id, "agent": f.agent, "severity": f.severity, "title": f.title, "is_accepted": f.is_accepted} for f in findings]


@router.post("/{review_id}/findings/{finding_id}/accept")
async def accept_finding(
    review_id: str,
    finding_id: str,
    org_id: str = Depends(_get_org_id),
):
    await _set_accepted(review_id, finding_id, org_id, True)
    return {"ok": True}


@router.post("/{review_id}/findings/{finding_id}/reject")
async def reject_finding(
    review_id: str,
    finding_id: str,
    org_id: str = Depends(_get_org_id),
):
    await _set_accepted(review_id, finding_id, org_id, False)
    return {"ok": True}


async def _set_accepted(review_id: str, finding_id: str, org_id: str, value: bool) -> None:
    async with session_context() as session:
        review_result = await session.execute(select(Review).where(Review.id == review_id, Review.org_id == org_id))
        if not review_result.scalar_one_or_none():
            raise HTTPException(status_code=404)
        finding_result = await session.execute(select(FindingModel).where(FindingModel.id == finding_id, FindingModel.review_id == review_id))
        finding = finding_result.scalar_one_or_none()
        if not finding:
            raise HTTPException(status_code=404)
        finding.is_accepted = value
        await session.commit()
