"""one_installation_multiple_repos

Revision ID: bbee977b5454
Revises: 657cb811832f
Create Date: 2026-05-17 11:30:33.938320

One installation can have multiple repos, so we need to change drop the unique constraint on installation_id
and add a new unique constraint on installation_id and full_name.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op, util

# revision identifiers, used by Alembic.
revision: str = "bbee977b5454"
down_revision: Union[str, Sequence[str], None] = "657cb811832f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("repos_installation_id_key"), "repos", type_="unique")
    op.create_unique_constraint("uq_repos_installation_id_full_name", "repos", ["installation_id", "full_name"])
    # uq_user_orgs_user_id_org_id already created inline in the user_orgs table definition


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT installation_id, COUNT(*) FROM repos GROUP BY installation_id HAVING COUNT(*) > 1")).fetchall()
    if result:
        dupes = ", ".join(str(r[0]) for r in result)
        raise util.CommandError(f"Cannot downgrade: duplicate installation_id values exist in repos ({dupes}). Clean up duplicates before rolling back this migration.")
    op.drop_constraint("uq_repos_installation_id_full_name", "repos", type_="unique")
    op.create_unique_constraint(op.f("repos_installation_id_key"), "repos", ["installation_id"], postgresql_nulls_not_distinct=False)
