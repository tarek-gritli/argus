from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .repo import Repo
    from .review import Review
    from .user_org import UserOrg


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    memberships: Mapped[list["UserOrg"]] = relationship("UserOrg", back_populates="org")
    repos: Mapped[list["Repo"]] = relationship("Repo", back_populates="org")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="org")
