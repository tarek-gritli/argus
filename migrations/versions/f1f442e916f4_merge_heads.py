"""merge_heads

Revision ID: f1f442e916f4
Revises: 7fbbfa640e37, a1b2c3d4e5f6
Create Date: 2026-05-25 20:00:00.000000

"""

from collections.abc import Sequence

revision: str = "f1f442e916f4"
down_revision: tuple[str, str] = ("7fbbfa640e37", "a1b2c3d4e5f6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
