"""add_org_invites_billing_email

Revision ID: c9d4e7a1b2f3
Revises: f1f442e916f4
Create Date: 2026-06-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d4e7a1b2f3"
down_revision: str | Sequence[str] | None = "f1f442e916f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("org_billing", sa.Column("billing_email", sa.String(), nullable=True))
    op.create_table(
        "org_invites",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("invited_by", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["orgs.id"]),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_org_invites_token", "org_invites", ["token"])
    op.create_index("ix_org_invites_org_id", "org_invites", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_org_invites_org_id", table_name="org_invites")
    op.drop_index("ix_org_invites_token", table_name="org_invites")
    op.drop_table("org_invites")
    op.drop_column("org_billing", "billing_email")
