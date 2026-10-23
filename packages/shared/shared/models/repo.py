from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .org import Org
    from .review import Review


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("orgs.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False, default="github", server_default="github")  # "github" | "gitlab"
    installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # GitHub App installation; NULL for GitLab
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    org: Mapped[Org] = relationship("Org", back_populates="repos")
    reviews: Mapped[list[Review]] = relationship("Review", back_populates="repo")

    __table_args__ = (
        UniqueConstraint("installation_id", "full_name", name="uq_repos_installation_id_full_name"),
        # GitLab repos have no installation_id, so identify them by (org, path)
        Index("uq_repos_gitlab_org_full_name", "org_id", "full_name", unique=True, postgresql_where="provider = 'gitlab'"),
    )
