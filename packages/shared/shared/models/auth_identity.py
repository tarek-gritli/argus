from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class AuthIdentity(Base):
    """One way a user can sign in: an account at an OAuth provider.

    `provider_host` distinguishes instances of the same provider (gitlab.com vs a
    self-hosted GitLab); it is "" for GitHub.
    """

    __tablename__ = "auth_identities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # "github" | "gitlab"
    provider_host: Mapped[str] = mapped_column(String, nullable=False, default="")
    provider_user_id: Mapped[str] = mapped_column(String, nullable=False)
    login: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped[User] = relationship("User", back_populates="identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_host", "provider_user_id", name="uq_auth_identities_subject"),
        UniqueConstraint("user_id", "provider", "provider_host", name="uq_auth_identities_user_provider"),
    )
