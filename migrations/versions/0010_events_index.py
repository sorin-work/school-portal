"""index events by child and by room, then time

Revision ID: 0010
Revises: 0009
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_events_child_occurred", "events", ["child_id", "occurred_at"])
    op.create_index("ix_events_room_occurred", "events", ["room_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_events_room_occurred", "events")
    op.drop_index("ix_events_child_occurred", "events")
