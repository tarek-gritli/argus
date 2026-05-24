import asyncio
import logging
from datetime import datetime, timezone

from fix_engine.pipeline import run_fix_pipeline
from integrations.github import PullRequestPayload, get_pr, get_pr_diff, get_pr_file_content, get_pr_files, post_findings_as_review, post_issue_comment, update_pr_body
from shared import dashboard_token
from shared.config import get_settings
from shared.db import fresh_session_context
from shared.models import Finding as FindingModel
from shared.models import Repo, Review
from shared.schemas import FindingSchema
from specialized.documentation.pr_description import generate_pr_description
from sqlalchemy import select

from .graph import run_review
from .quota import check_and_increment_quota, get_or_create_billing

logger = logging.getLogger(__name__)

_AGENT_LABELS = {
    "security": "Security",
    "quality": "Quality",
    "testing": "Testing",
    "documentation": "Documentation",
    "ticket_compliance": "Ticket Compliance",
}

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def run(payload: dict) -> None:
    try:
        org_id = payload.get("org_id", "")
        pr_payload = PullRequestPayload(**payload)
        pr = get_pr(pr_payload.repo_full_name, pr_payload.pr_number, pr_payload.installation_id)
        pr_payload.pr_title = pr.title or ""
        pr_payload.pr_body = pr.body or ""
        files = get_pr_files(pr)

        if not files:
            post_issue_comment(pr, "⚠️ No changes detected in this PR.")
            return

        if org_id and asyncio.run(_already_reviewed(org_id, pr_payload.repo_full_name, pr_payload.installation_id, pr_payload.head_sha)):
            logger.info("Skipping review — head_sha %s already reviewed", pr_payload.head_sha[:8])
            return

        if org_id:
            allowed = asyncio.run(_check_quota(org_id))
            if not allowed:
                post_issue_comment(pr, "⚠️ Argus review quota reached for this billing period. Upgrade your plan to continue.")
                return

        diff = get_pr_diff(pr)
        findings = run_review(files=files, diff=diff, pr_payload=pr_payload)

        files_content: dict[str, str] = {}
        for finding in findings:
            if finding.file not in files_content:
                content = get_pr_file_content(pr, finding.file)
                if content is not None:
                    files_content[finding.file] = content

        findings = run_fix_pipeline(findings, files_content)

        # Auto-generate and update PR description if it's missing or too short
        pr_description = generate_pr_description(diff, pr.title, pr.body or "")
        if pr_description and pr_description != pr.body:
            try:
                update_pr_body(pr, pr_description)
                logger.info("PR description updated.")
            except Exception:
                logger.warning("Failed to update PR description — continuing", exc_info=True)

        # Build dashboard link if a public URL is configured
        dashboard_url = _build_dashboard_url(pr_payload.repo_full_name, pr_payload.pr_number)

        # Post inline review suggestions for findings with fixes; summary comment for all findings
        post_findings_as_review(pr, findings, pr_payload.head_sha)
        post_issue_comment(pr, _format_findings(findings, dashboard_url))

        if org_id:
            try:
                asyncio.run(_persist(org_id=org_id, pr_payload=pr_payload, findings=findings))
            except Exception:
                logger.exception("Review persisted to GitHub, but DB persistence failed")

    except Exception:
        logger.exception("Orchestration failed")
        raise


async def _already_reviewed(org_id: str, repo_full_name: str, installation_id: int, head_sha: str) -> bool:
    async with fresh_session_context() as session:
        repo_result = await session.execute(select(Repo).where(Repo.installation_id == installation_id, Repo.full_name == repo_full_name))
        repo = repo_result.scalar_one_or_none()
        if not repo:
            return False
        result = await session.execute(
            select(Review.id)
            .where(
                Review.org_id == org_id,
                Review.repo_id == repo.id,
                Review.head_sha == head_sha,
                Review.status == "completed",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


async def _check_quota(org_id: str) -> bool:
    async with fresh_session_context() as session:
        billing = await get_or_create_billing(session, org_id)
        return await check_and_increment_quota(session, billing)


async def _persist(org_id: str, pr_payload: PullRequestPayload, findings: list[FindingSchema]) -> None:
    async with fresh_session_context() as session:
        result = await session.execute(select(Repo).where(Repo.installation_id == pr_payload.installation_id, Repo.full_name == pr_payload.repo_full_name))
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repo not found for installation_id={pr_payload.installation_id} full_name={pr_payload.repo_full_name}")
        repo_id = repo.id

        review = Review(
            org_id=org_id,
            repo_id=repo_id,
            pr_number=pr_payload.pr_number,
            head_sha=pr_payload.head_sha,
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        session.add(review)
        await session.flush()

        for f in findings:
            session.add(
                FindingModel(
                    review_id=review.id,
                    agent=f.agent,
                    severity=f.severity,
                    file=f.file,
                    line_start=f.line_start,
                    line_end=f.line_end,
                    title=f.title,
                    description=f.description,
                    suggestion=f.suggestion,
                    confidence=f.confidence,
                )
            )
        await session.commit()


def _build_dashboard_url(repo_full_name: str, pr_number: int) -> str | None:
    settings = get_settings()
    if not settings.public_url:
        return None
    owner, repo = repo_full_name.split("/", 1)
    signing_secret = settings.dashboard_token_secret or settings.jwt_secret_key
    token = dashboard_token.sign(signing_secret, repo_full_name, pr_number)
    return f"{settings.public_url.rstrip('/')}/dashboard/{owner}/{repo}/{pr_number}?token={token}"


def _format_findings(findings: list[FindingSchema], dashboard_url: str | None = None) -> str:
    if not findings:
        return "✅ No issues found across all review agents."

    by_agent: dict[str, dict[str, list[FindingSchema]]] = {}
    for f in findings:
        by_agent.setdefault(f.agent, {}).setdefault(f.severity, []).append(f)

    lines = ["## Argus Code Review\n"]

    if dashboard_url:
        lines.append(f"🔗 **[View full interactive report →]({dashboard_url})**\n")

    _AGENT_ORDER = ("security", "quality", "testing", "documentation")
    ordered = [k for k in _AGENT_ORDER if k in by_agent]
    ordered += [k for k in by_agent if k not in _AGENT_ORDER]

    for agent_key in ordered:
        lines.append(f"### {_AGENT_LABELS.get(agent_key, agent_key.title())} Review\n")
        for severity in _SEVERITY_ORDER:
            bucket = by_agent[agent_key].get(severity, [])
            if not bucket:
                continue
            lines.append(f"#### {severity.upper()}\n")
            for finding in bucket:
                lines.append(f"**{finding.title}** (`{finding.file}:{finding.line_start}-{finding.line_end}`)\n")
                lines.append(f"{finding.description}\n")
                if finding.suggestion:
                    lines.append(f"> Suggestion: {finding.suggestion}\n")
                if finding.fix:
                    lines.append(f"<details>\n<summary>💡 Suggested Fix: <i>{finding.fix.description}</i></summary>\n")
                    lines.append(f"```\n{finding.fix.diff}\n```\n</details>\n")
                lines.append("")

    return "\n".join(lines)
