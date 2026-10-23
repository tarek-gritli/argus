"""repo_provider

Revision ID: d1a7b3c9e5f2
Revises: f1f442e916f4
Create Date: 2026-06-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1a7b3c9e5f2"
down_revision: str | Sequence[str] | None = "f1f442e916f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("repos", sa.Column("provider", sa.String(), server_default="github", nullable=False))
    op.alter_column("repos", "installation_id", existing_type=sa.Integer(), nullable=True)
    op.create_index(
        "uq_repos_gitlab_org_full_name",
        "repos",
        ["org_id", "full_name"],
        unique=True,
        postgresql_where=sa.text("provider = 'gitlab'"),
    )


def downgrade() -> None:
    op.drop_index("uq_repos_gitlab_org_full_name", table_name="repos")
    # GitLab repos have no installation_id and cannot exist in the old schema
    op.execute("DELETE FROM repos WHERE provider = 'gitlab'")
    op.alter_column("repos", "installation_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("repos", "provider")
