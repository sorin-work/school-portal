"""incidents and accidents a parent acknowledges

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events", sa.Column("needs_ack", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("events", sa.Column("acknowledged_at", sa.DateTime(timezone=True)))
    op.add_column(
        "events",
        sa.Column(
            "acknowledged_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "acknowledged_by_id")
    op.drop_column("events", "acknowledged_at")
    op.drop_column("events", "needs_ack")
