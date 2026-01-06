"""rooms and the staff who work in them

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("age_range", sa.String(40)),
        sa.Column("capacity", sa.Integer()),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "room_staff",
        sa.Column(
            "room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("is_lead", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("room_staff")
    op.drop_table("rooms")
