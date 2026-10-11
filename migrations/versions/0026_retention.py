"""leaving date, deletion date and hold on children

Revision ID: 0026
Revises: 0025
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("children", sa.Column("left_on", sa.Date()))
    op.add_column("children", sa.Column("purge_after", sa.Date()))
    op.add_column(
        "children",
        sa.Column("retention_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("children", "retention_hold")
    op.drop_column("children", "purge_after")
    op.drop_column("children", "left_on")
