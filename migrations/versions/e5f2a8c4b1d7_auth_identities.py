"""auth_identities

Merges the invites and repo-provider heads, moves sign-in identity out of `users`
into `auth_identities` (so GitLab and GitHub accounts are interchangeable), and lifts
the one-owned-org-per-user limit.

Revision ID: e5f2a8c4b1d7
Revises: c9d4e7a1b2f3, d1a7b3c9e5f2
Create Date: 2026-06-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "e5f2a8c4b1d7"
down_revision: str | Sequence[str] | None = ("c9d4e7a1b2f3", "d1a7b3c9e5f2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_host", sa.String(), nullable=False),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("login", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_host", "provider_user_id", name="uq_auth_identities_subject"),
        sa.UniqueConstraint("user_id", "provider", "provider_host", name="uq_auth_identities_user_provider"),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])

    # Every existing user signed in with GitHub.
    op.execute(
        """
        INSERT INTO auth_identities (id, user_id, provider, provider_host, provider_user_id, login, avatar_url, created_at)
        SELECT gen_random_uuid()::text, id, 'github', '', github_id::text, github_login, avatar_url, created_at
        FROM users
        """
    )

    op.alter_column("users", "github_login", new_column_name="login")
    op.drop_column("users", "github_id")
    op.drop_index("uq_user_orgs_owner_per_user", table_name="user_orgs", postgresql_where=sa.text("role = 'owner'"))


def downgrade() -> None:
    op.add_column("users", sa.Column("github_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE users SET github_id = i.provider_user_id::integer
        FROM auth_identities i
        WHERE i.user_id = users.id AND i.provider = 'github'
        """
    )
    if not context.is_offline_mode() and op.get_bind().execute(sa.text("SELECT 1 FROM users WHERE github_id IS NULL LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade: some users have no GitHub identity (GitLab-only sign-ups)")
    op.alter_column("users", "github_id", nullable=False)
    op.create_unique_constraint("users_github_id_key", "users", ["github_id"])
    op.alter_column("users", "login", new_column_name="github_login")
    # Fails (by design) if any user now owns more than one org
    op.create_index(
        "uq_user_orgs_owner_per_user",
        "user_orgs",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("role = 'owner'"),
    )
    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_table("auth_identities")
