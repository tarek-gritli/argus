from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .auth_identity import AuthIdentity
    from .user_org import UserOrg


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    login: Mapped[str] = mapped_column(String, nullable=False)  # display name; sign-in lives in AuthIdentity
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    memberships: Mapped[list[UserOrg]] = relationship("UserOrg", back_populates="user")
    identities: Mapped[list[AuthIdentity]] = relationship("AuthIdentity", back_populates="user")
