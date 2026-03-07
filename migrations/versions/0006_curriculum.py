"""curriculum areas for learning observations

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curriculum_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework", sa.String(20), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.add_column(
        "events",
        sa.Column(
            "area_id", sa.Integer(), sa.ForeignKey("curriculum_areas.id", ondelete="SET NULL")
        ),
    )


def downgrade() -> None:
    op.drop_column("events", "area_id")
    op.drop_table("curriculum_areas")
