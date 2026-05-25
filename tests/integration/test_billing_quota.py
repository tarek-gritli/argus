"""
Integration tests for billing/quota scenarios end-to-end through coordinator.run().

GitHub API calls, LLM calls, DB session, and fix pipeline are all mocked — the real code
path under test is the coordinator's quota gate: get_or_create_billing →
check_and_increment_quota → conditional review execution or blocked comment.

Pattern mirrors test_pipeline.py: patches applied as context managers, coordinator
imported inside the with-block so the patched names are already bound.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from shared.models.org_billing import OrgBilling


def _make_factory(billing: OrgBilling):
    """Return a callable that acts as async_sessionmaker, creating a fresh session each call."""

    def factory():
        return _make_session_ctx(billing)

    return factory


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

DIFF = """\
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,3 +1,5 @@
+SECRET_KEY = "sk_live_ABC123"
+
 def get_user(uid):
     return db.query(f"SELECT * FROM users WHERE id = {uid}")
"""

BASE_PAYLOAD = {
    "action": "opened",
    "repo_full_name": "owner/repo",
    "pr_number": 1,
    "head_sha": "abc123",
    "base_sha": "base456",
    "installation_id": 42,
}


def _make_pr():
    pr = MagicMock()
    pr.title = "Fix auth"
    pr.body = ""
    return pr


def _make_files():
    f = MagicMock()
    f.filename = "src/auth.py"
    f.patch = "@@ -1,3 +1,5 @@\n+SECRET_KEY = 'sk'\n"
    return [f]


def _billing(plan="free", seat_count=1, reviews_used=0, reset_days=30):
    b = OrgBilling(org_id="org-1", plan=plan, seat_count=seat_count, reviews_used_this_month=reviews_used)
    b.quota_reset_at = datetime.now(timezone.utc) + timedelta(days=reset_days)
    return b


def _make_session_ctx(billing: OrgBilling):
    """Async context manager yielding a mock session whose SELECT returns billing."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = billing
    result.scalar_one.return_value = billing
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()

    @asynccontextmanager
    async def _ctx():
        yield session

    return _ctx()


def _run(payload: dict, billing: OrgBilling, post_comment: MagicMock, post_review: MagicMock | None = None):
    """Run coordinator.run() with all external deps patched."""
    mock_factory = _make_factory(billing)
    with (
        patch("orchestrator.coordinator.get_pr", return_value=_make_pr()),
        patch("orchestrator.coordinator.get_pr_files", return_value=_make_files()),
        patch("orchestrator.coordinator.get_pr_diff", return_value=DIFF),
        patch("orchestrator.coordinator.get_pr_file_content", return_value="mock content"),
        patch("orchestrator.coordinator.run_async", side_effect=lambda coro, **_: _run_coro(coro)),
        patch("orchestrator.coordinator.get_session_factory", return_value=mock_factory),
        patch("orchestrator.coordinator._already_reviewed", new=AsyncMock(return_value=False)),
        patch("orchestrator.coordinator.get_or_create_billing", return_value=billing),
        patch("orchestrator.coordinator.check_and_increment_quota", side_effect=_real_check(billing)),
        patch("specialized.quality.agent._call_claude", return_value="[]"),
        patch("specialized.testing.agent._call_claude", return_value="[]"),
        patch("orchestrator.graph.documentation_analyze", return_value=[]),
        patch("orchestrator.coordinator.run_fix_pipeline", side_effect=lambda f, _: f),
        patch("orchestrator.coordinator.generate_pr_description", return_value=""),
        patch("orchestrator.coordinator.update_pr_body"),
        patch("orchestrator.coordinator.post_findings_as_review", new=post_review or MagicMock()),
        patch("orchestrator.coordinator.post_issue_comment", new=post_comment),
        patch("orchestrator.coordinator._persist", new=AsyncMock()),
    ):
        from orchestrator.coordinator import run

        run(payload)


def _run_coro(coro):
    """Run a coroutine synchronously — test stand-in for run_async()."""
    import asyncio

    return asyncio.run(coro)


def _real_check(billing: OrgBilling):
    """Delegate to the real check_and_increment_quota logic using billing directly."""
    from orchestrator.quota import check_and_increment_quota

    async def async_check(session, b):
        return await check_and_increment_quota(session, b)

    return async_check


# ---------------------------------------------------------------------------
# quota gate — blocked vs allowed
# ---------------------------------------------------------------------------


class TestQuotaGate:
    def test_free_org_within_quota_review_runs(self):
        """Free org with 10/50 reviews — review executes, no blocked message."""
        billing = _billing(plan="free", reviews_used=10)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        assert post_comment.called
        body = post_comment.call_args[0][1]
        assert "quota reached" not in body.lower()

    def test_free_org_at_quota_limit_blocked(self):
        """Free org at 50/50 — review is blocked and quota-reached comment posted."""
        billing = _billing(plan="free", reviews_used=50)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        assert post_comment.called
        body = post_comment.call_args[0][1]
        assert "quota reached" in body.lower()

    def test_no_org_id_skips_quota_check(self):
        """Payload without org_id bypasses quota entirely — review always runs."""
        billing = _billing(plan="free", reviews_used=50)  # would block if checked
        post_comment = MagicMock()
        _run(BASE_PAYLOAD, billing, post_comment)  # no org_id

        body = post_comment.call_args[0][1]
        assert "quota reached" not in body.lower()

    def test_pro_plan_5_seats_allows_100_reviews(self):
        """Pro plan with 5 seats has 100-review limit; at 99 → still allowed."""
        billing = _billing(plan="pro", seat_count=5, reviews_used=99)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        body = post_comment.call_args[0][1]
        assert "quota reached" not in body.lower()

    def test_pro_plan_at_seat_limit_blocked(self):
        """Pro plan with 5 seats at 100/100 → blocked."""
        billing = _billing(plan="pro", seat_count=5, reviews_used=100)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        body = post_comment.call_args[0][1]
        assert "quota reached" in body.lower()

    def test_team_plan_10_seats_allows_200_reviews(self):
        """Team plan with 10 seats has 200-review limit; at 199 → still allowed."""
        billing = _billing(plan="team", seat_count=10, reviews_used=199)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        body = post_comment.call_args[0][1]
        assert "quota reached" not in body.lower()

    def test_team_plan_at_seat_limit_blocked(self):
        """Team plan with 10 seats at 200/200 → blocked."""
        billing = _billing(plan="team", seat_count=10, reviews_used=200)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        body = post_comment.call_args[0][1]
        assert "quota reached" in body.lower()

    def test_monthly_reset_unblocks_org(self):
        """Org was at limit last month; quota_reset_at in the past → reset → review runs."""
        billing = _billing(plan="free", reviews_used=50, reset_days=-1)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        body = post_comment.call_args[0][1]
        assert "quota reached" not in body.lower()
        assert billing.reviews_used_this_month == 1  # reset to 0 then incremented


# ---------------------------------------------------------------------------
# quota counter side-effects
# ---------------------------------------------------------------------------


class TestQuotaIncrement:
    def test_successful_review_increments_counter(self):
        """After a review runs, reviews_used_this_month is incremented by 1."""
        billing = _billing(plan="free", reviews_used=5)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        assert billing.reviews_used_this_month == 6

    def test_blocked_review_does_not_increment_counter(self):
        """When quota is exceeded the counter must not increase."""
        billing = _billing(plan="free", reviews_used=50)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        assert billing.reviews_used_this_month == 50

    def test_last_allowed_review_reaches_limit(self):
        """The 50th review on a free plan is allowed and brings the count to exactly 50."""
        billing = _billing(plan="free", reviews_used=49)
        post_comment = MagicMock()
        _run({**BASE_PAYLOAD, "org_id": "org-1"}, billing, post_comment)

        assert billing.reviews_used_this_month == 50
        body = post_comment.call_args[0][1]
        assert "quota reached" not in body.lower()
