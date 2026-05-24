import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

_FREE_QUOTA = 50
_REVIEWS_PER_SEAT = 20


def _next_month_start() -> datetime:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


class OrgBilling(Base):
    __tablename__ = "org_billing"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("orgs.id"), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String, default="free")  # "free" | "pro" | "team" | "enterprise"
    seat_count: Mapped[int] = mapped_column(Integer, default=1)
    reviews_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    quota_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: _next_month_start(),
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    __table_args__ = (
        CheckConstraint("seat_count >= 1", name="ck_org_billing_seat_count_positive"),
        CheckConstraint("reviews_used_this_month >= 0", name="ck_org_billing_reviews_used_non_negative"),
    )

    def __init__(
        self,
        org_id: str,
        plan: str = "free",
        seat_count: int = 1,
        reviews_used_this_month: int = 0,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        **kwargs,
    ):
        super().__init__(
            org_id=org_id,
            plan=plan,
            seat_count=seat_count,
            reviews_used_this_month=reviews_used_this_month,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            **kwargs,
        )

    @property
    def monthly_limit(self) -> int:
        if self.plan == "free":
            return _FREE_QUOTA
        return self.seat_count * _REVIEWS_PER_SEAT
