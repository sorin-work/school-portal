"""messages about a child

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "child_id",
            sa.Integer(),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_messages_child_id", "messages", ["child_id"])
    op.create_table(
        "message_reads",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "child_id",
            sa.Integer(),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("last_read_id", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("message_reads")
    op.drop_table("messages")
