from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .repo import Repo
    from .review import Review
    from .user import User

_PLAN_QUOTAS = {"free": 50, "pro": 500, "team": -1}


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    plan: Mapped[str] = mapped_column(String, default="free")
    review_quota: Mapped[int] = mapped_column(Integer, default=50)
    reviews_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    quota_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: _next_month_start(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="org")
    repos: Mapped[list["Repo"]] = relationship("Repo", back_populates="org")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="org")

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("plan", "free")
        kwargs.setdefault("reviews_used_this_month", 0)
        plan = kwargs["plan"]
        if "review_quota" not in kwargs:
            kwargs["review_quota"] = _PLAN_QUOTAS.get(str(plan), 50)
        super().__init__(**kwargs)


def _next_month_start() -> datetime:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
