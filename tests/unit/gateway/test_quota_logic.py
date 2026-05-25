"""
Unit tests for orchestrator/quota.py — get_or_create_billing and check_and_increment_quota.
All DB interaction is mocked; these tests cover the logic branches in isolation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from shared.models.org_billing import OrgBilling
from sqlalchemy.exc import IntegrityError

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _billing(org_id="org-1", plan="free", seat_count=1, reviews_used=0, reset_offset_days=30):
    """Build an OrgBilling instance with quota_reset_at in the future by default."""
    b = OrgBilling(org_id=org_id, plan=plan, seat_count=seat_count, reviews_used_this_month=reviews_used)
    b.quota_reset_at = datetime.now(timezone.utc) + timedelta(days=reset_offset_days)
    return b


def _session(billing: OrgBilling | None):
    """Mock AsyncSession whose SELECT returns the given billing row (or None)."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = billing
    result.scalar_one.return_value = billing
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# get_or_create_billing
# ---------------------------------------------------------------------------


class TestGetOrCreateBilling:
    @pytest.mark.asyncio
    async def test_returns_existing_record(self):
        existing = _billing()
        session = _session(existing)

        from orchestrator.quota import get_or_create_billing

        result = await get_or_create_billing(session, "org-1")

        assert result is existing
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_record_when_missing(self):
        session = _session(None)

        from orchestrator.quota import get_or_create_billing

        result = await get_or_create_billing(session, "org-new")

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.org_id == "org-new"
        assert result.plan == "free"

    @pytest.mark.asyncio
    async def test_integrity_error_race_falls_back_to_select(self):
        """Simulates two workers racing to insert the first billing row — the loser retries SELECT."""
        existing = _billing()
        session = AsyncMock()
        session.flush = AsyncMock(side_effect=IntegrityError("dup", {}, Exception("duplicate key")))
        session.rollback = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        # First SELECT returns None (triggers insert); second SELECT (after rollback) returns existing row
        result_none = MagicMock()
        result_none.scalar_one_or_none.return_value = None
        result_existing = MagicMock()
        result_existing.scalar_one_or_none.return_value = existing
        result_existing.scalar_one.return_value = existing

        session.execute = AsyncMock(side_effect=[result_none, result_existing])

        from orchestrator.quota import get_or_create_billing

        result = await get_or_create_billing(session, "org-1")

        session.rollback.assert_called_once()
        assert result is existing


# ---------------------------------------------------------------------------
# check_and_increment_quota
# ---------------------------------------------------------------------------


class TestCheckAndIncrementQuota:
    @pytest.mark.asyncio
    async def test_under_limit_returns_true_and_increments(self):
        billing = _billing(reviews_used=10)  # free plan, limit=50
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, plan = await check_and_increment_quota(session, billing)

        assert allowed is True
        assert plan == "free"
        assert billing.reviews_used_this_month == 11
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_at_limit_returns_false(self):
        billing = _billing(reviews_used=50)  # free plan, limit=50 — exactly at cap
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, plan = await check_and_increment_quota(session, billing)

        assert allowed is False
        assert plan == "free"
        assert billing.reviews_used_this_month == 50  # not incremented
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_over_limit_returns_false(self):
        billing = _billing(reviews_used=99)
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, _ = await check_and_increment_quota(session, billing)

        assert allowed is False

    @pytest.mark.asyncio
    async def test_monthly_reset_when_past_reset_date(self):
        """When quota_reset_at is in the past the counter resets before checking."""
        billing = _billing(reviews_used=50, reset_offset_days=-1)  # reset date yesterday
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, _ = await check_and_increment_quota(session, billing)

        assert allowed is True
        assert billing.reviews_used_this_month == 1  # reset to 0, then incremented
        # quota_reset_at updated to next month
        assert billing.quota_reset_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_reset_sets_next_month_boundary(self):
        billing = _billing(reviews_used=50, reset_offset_days=-1)
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        await check_and_increment_quota(session, billing)

        now = datetime.now(timezone.utc)
        assert billing.quota_reset_at.day == 1
        assert billing.quota_reset_at.hour == 0
        assert billing.quota_reset_at > now

    @pytest.mark.asyncio
    async def test_pro_plan_seat_based_limit(self):
        billing = _billing(plan="pro", seat_count=5, reviews_used=499)  # limit=500 (5×100)
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, plan = await check_and_increment_quota(session, billing)

        assert allowed is True
        assert plan == "pro"
        assert billing.reviews_used_this_month == 500

    @pytest.mark.asyncio
    async def test_pro_plan_at_seat_limit_blocked(self):
        billing = _billing(plan="pro", seat_count=5, reviews_used=500)  # limit=500 (5×100)
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, _ = await check_and_increment_quota(session, billing)

        assert allowed is False

    @pytest.mark.asyncio
    async def test_team_plan_seat_based_limit(self):
        billing = _billing(plan="team", seat_count=10, reviews_used=999)  # limit=1000 (10×100)
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, _ = await check_and_increment_quota(session, billing)

        assert allowed is True

    @pytest.mark.asyncio
    async def test_first_review_on_new_org(self):
        billing = _billing(reviews_used=0)
        session = _session(billing)

        from orchestrator.quota import check_and_increment_quota

        allowed, _ = await check_and_increment_quota(session, billing)

        assert allowed is True
        assert billing.reviews_used_this_month == 1
