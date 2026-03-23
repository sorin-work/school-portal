"""photo consent per child

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "children",
        sa.Column("photo_consent", sa.String(8), nullable=False, server_default="none"),
    )


def downgrade() -> None:
    op.drop_column("children", "photo_consent")
