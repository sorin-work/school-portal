"""attendance register

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "child_id",
            sa.Integer(),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="SET NULL")),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_in_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("checked_out_at", sa.DateTime(timezone=True)),
        sa.Column(
            "checked_out_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("collected_by", sa.String(120)),
        sa.Column("note", sa.Text()),
    )
    op.create_index("ix_attendance_day", "attendance", ["day"])


def downgrade() -> None:
    op.drop_table("attendance")
