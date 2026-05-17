from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .org import Org
    from .user import User


class UserOrg(Base):
    __tablename__ = "user_orgs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String, ForeignKey("orgs.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, default="member")  # "owner" | "member"
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship("User", back_populates="memberships")
    org: Mapped[Org] = relationship("Org", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_user_orgs_user_id_org_id"),
        Index(
            "uq_user_orgs_owner_per_user",
            "user_id",
            unique=True,
            postgresql_where="role = 'owner'",
        ),
    )
