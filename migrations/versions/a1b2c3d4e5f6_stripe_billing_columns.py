"""stripe_billing_columns

Revision ID: a1b2c3d4e5f6
Revises: f3961ade6392
Create Date: 2026-05-24 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f3961ade6392"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("org_billing", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("org_billing", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.create_index("ix_org_billing_stripe_customer_id", "org_billing", ["stripe_customer_id"], unique=True)
    op.create_unique_constraint("uq_org_billing_stripe_sub_id", "org_billing", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_constraint("uq_org_billing_stripe_sub_id", "org_billing", type_="unique")
    op.drop_index("ix_org_billing_stripe_customer_id", table_name="org_billing")
    op.drop_column("org_billing", "stripe_subscription_id")
    op.drop_column("org_billing", "stripe_customer_id")
