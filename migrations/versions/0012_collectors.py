"""authorised collectors with photos

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "child_id",
            sa.Integer(),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("relationship", sa.String(40)),
        sa.Column("phone", sa.String(40)),
        sa.Column("photo_id", sa.String(32), sa.ForeignKey("media.id", ondelete="SET NULL")),
        sa.Column("password_hint", sa.String(80)),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "attendance",
        sa.Column(
            "collector_id", sa.Integer(), sa.ForeignKey("collectors.id", ondelete="SET NULL")
        ),
    )


def downgrade() -> None:
    op.drop_column("attendance", "collector_id")
    op.drop_table("collectors")
