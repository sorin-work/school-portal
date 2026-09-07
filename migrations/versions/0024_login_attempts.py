"""sign-in attempts for rate limiting

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index("ix_login_attempts_email", "login_attempts", ["email"])
    op.create_index("ix_login_attempts_ip", "login_attempts", ["ip"])


def downgrade() -> None:
    op.drop_table("login_attempts")
