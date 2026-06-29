"""notices for families

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_on", sa.Date()),
        sa.Column("pinned", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "notice_rooms",
        sa.Column(
            "notice_id",
            sa.Integer(),
            sa.ForeignKey("notices.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
        ),
    )


def downgrade() -> None:
    op.drop_table("notice_rooms")
    op.drop_table("notices")
