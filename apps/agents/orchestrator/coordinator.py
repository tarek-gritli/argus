import logging
from datetime import datetime, timezone

from context.bundle import ContextBundle
from context.embeddings import search_similar
from context.history import get_rejected_finding_keys, suppress_duplicate_findings
from fix_engine.pipeline import run_fix_pipeline
from integrations.notifications.dispatcher import dispatch_review_completed
from integrations.notifications.schemas import ReviewSummary
from shared.models import Finding as FindingModel
from shared.models import Repo, Review
from shared.schemas import FindingSchema
from shared.telemetry import create_trace, langfuse_context
from shared.telemetry import flush as flush_telemetry
from specialized.documentation.pr_description import generate_pr_description
from sqlalchemy import select
from workers.connections import get_session_factory, run_async

from .formatter import format_findings
from .graph import run_review
from .quota import check_and_increment_quota, get_or_create_billing
from .vcs import UnifiedPayload, VCSProvider, get_vcs_provider

logger = logging.getLogger(__name__)


def run(payload: dict) -> None:
    try:
        provider, pr_payload = get_vcs_provider(payload)
        org_id = pr_payload.org_id

        trace = None
        if langfuse_context:
            trace = create_trace(
                name=f"PR #{pr_payload.pr_id} — {pr_payload.repo_id}",
                user_id=org_id or "anonymous",
                tags=["pr-review"],
                metadata={
                    "platform": pr_payload.platform,
                    "repo": pr_payload.repo_id,
                    "pr_number": pr_payload.pr_id,
                    "head_sha": pr_payload.head_sha,
                    "plan": payload.get("plan", "free"),
                },
            )

        files = provider.get_files()

        if not files:
            provider.post_issue_comment("⚠️ No changes detected in this PR.")
            return

        if org_id and run_async(_already_reviewed(org_id, pr_payload)):
            logger.info("Skipping review — head_sha %s already reviewed", pr_payload.head_sha[:8])
            return

        plan = "free"
        if org_id:
            allowed, plan = run_async(_check_quota(org_id))
            if not allowed:
                provider.post_issue_comment("⚠️ Argus review quota reached for this billing period. Upgrade your plan to continue.")
                return

        diff = provider.get_diff()
        repo_id = run_async(_get_repo_id_for_run(pr_payload)) if org_id else None
        context = run_async(_fetch_context(repo_id=repo_id, diff=diff)) if repo_id else ContextBundle.empty()
        findings = run_review(files=files, diff=diff, pr_payload=pr_payload, plan=plan, context=context)

        if org_id and repo_id:
            rejected_keys = run_async(get_rejected_finding_keys(org_id=org_id, repo_id=repo_id))
            findings = suppress_duplicate_findings(findings, rejected_keys)

        files_content: dict[str, str] = {}
        for finding in findings:
            if finding.file not in files_content:
                content = provider.get_file_content(finding.file)
                if content is not None:
                    files_content[finding.file] = content

        findings = run_fix_pipeline(findings, files_content)

        pr_description = generate_pr_description(diff, provider.title, provider.body)
        if pr_description and pr_description != provider.body:
            try:
                provider.update_description(pr_description)
                logger.info("PR description updated.")
            except Exception:
                logger.warning("Failed to update PR description — continuing", exc_info=True)

        provider.post_issue_comment(format_findings(findings))

        try:
            provider.post_findings_as_review(findings, pr_payload.head_sha)
        except Exception:
            logger.exception("Failed to post inline review comments — summary comment was already posted")

        if org_id:
            try:
                run_async(_persist(org_id=org_id, pr_payload=pr_payload, findings=findings))
            except Exception:
                logger.exception("Review posted, but DB persistence failed")
            if plan in {"team", "enterprise"}:
                try:
                    run_async(_notify(org_id=org_id, pr_payload=pr_payload, provider=provider, findings=findings))
                except Exception:
                    logger.exception("Notifications failed — review still posted")

        if trace is not None:
            try:
                trace.update(output={"findings_count": len(findings), "agents_run": list({f.agent for f in findings})})
            except Exception:
                pass

    except Exception:
        logger.exception("Orchestration failed")
        raise
    finally:
        flush_telemetry()


def _repo_query(p: UnifiedPayload):
    """GitHub repos are keyed by (installation, name); GitLab repos by (org, provider, path)."""
    if p.platform == "gitlab":
        return select(Repo).where(Repo.org_id == p.org_id, Repo.provider == "gitlab", Repo.full_name == p.repo_id)
    return select(Repo).where(Repo.installation_id == p.installation_id, Repo.full_name == p.repo_id)


async def _already_reviewed(org_id: str, pr_payload: UnifiedPayload) -> bool:
    async with get_session_factory()() as session:
        repo_result = await session.execute(_repo_query(pr_payload))
        repo = repo_result.scalar_one_or_none()
        if not repo:
            return False
        result = await session.execute(
            select(Review.id)
            .where(
                Review.org_id == org_id,
                Review.repo_id == repo.id,
                Review.head_sha == pr_payload.head_sha,
                Review.status == "completed",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


async def _get_repo_id_for_run(pr_payload: UnifiedPayload) -> str | None:
    async with get_session_factory()() as session:
        result = await session.execute(_repo_query(pr_payload))
        repo = result.scalar_one_or_none()
        return repo.id if repo else None


async def _fetch_context(repo_id: str, diff: str) -> ContextBundle:
    try:
        similar = await search_similar(repo_id, diff, top_k=5)
        return ContextBundle(similar_chunks=similar, repo_id=repo_id)
    except Exception:
        logger.warning("_fetch_context failed — using empty context", exc_info=True)
        return ContextBundle.empty()


async def _check_quota(org_id: str) -> tuple[bool, str]:
    async with get_session_factory()() as session:
        billing = await get_or_create_billing(session, org_id)
        return await check_and_increment_quota(session, billing)


async def _persist(org_id: str, pr_payload: UnifiedPayload, findings: list[FindingSchema]) -> None:
    async with get_session_factory()() as session:
        result = await session.execute(_repo_query(pr_payload))
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repo not found for {pr_payload.platform}:{pr_payload.repo_id}")
        repo_id = repo.id

        review = Review(
            org_id=org_id,
            repo_id=repo_id,
            pr_number=pr_payload.pr_id,
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


async def _notify(org_id: str, pr_payload: UnifiedPayload, provider: VCSProvider, findings: list[FindingSchema]) -> None:
    summary = ReviewSummary(
        org_id=org_id,
        repo=pr_payload.repo_id,
        pr_number=pr_payload.pr_id,
        pr_url=provider.url,
        finding_count=len(findings),
        critical_count=sum(1 for f in findings if f.severity == "critical"),
        high_count=sum(1 for f in findings if f.severity == "high"),
    )
    async with get_session_factory()() as session:
        await dispatch_review_completed(session, summary)
