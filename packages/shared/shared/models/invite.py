from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class OrgInvite(Base):
    __tablename__ = "org_invites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("orgs.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="member")
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    invited_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_expires_at)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_org_invites_token", "token"),
        Index("ix_org_invites_org_id", "org_id"),
    )

    def __init__(self, **kwargs):
        # Column defaults only fire at flush; set them here so a fresh instance is usable.
        kwargs.setdefault("role", "member")
        kwargs.setdefault("token", str(uuid.uuid4()))
        kwargs.setdefault("expires_at", _expires_at())
        kwargs.setdefault("accepted_at", None)
        super().__init__(**kwargs)
