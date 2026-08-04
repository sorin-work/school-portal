"""who limited a guardian's access and why

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("guardians", sa.Column("restriction_reason", sa.Text()))
    op.add_column(
        "guardians",
        sa.Column("restricted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.add_column("guardians", sa.Column("restricted_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("guardians", "restricted_at")
    op.drop_column("guardians", "restricted_by_id")
    op.drop_column("guardians", "restriction_reason")
