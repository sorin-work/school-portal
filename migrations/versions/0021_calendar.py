"""school calendar with replies and trip consent

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("location", sa.String(160)),
        sa.Column("rsvp_required", sa.Boolean(), nullable=False),
        sa.Column("consent_required", sa.Boolean(), nullable=False),
        sa.Column("consent_text", sa.Text()),
        sa.Column("respond_by", sa.Date()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "school_event_rooms",
        sa.Column(
            "school_event_id",
            sa.Integer(),
            sa.ForeignKey("school_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "rsvps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "school_event_id",
            sa.Integer(),
            sa.ForeignKey("school_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_id",
            sa.Integer(),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attending", sa.Boolean(), nullable=False),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column("signed_name", sa.String(120)),
        sa.Column("note", sa.Text()),
        sa.Column("responded_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("school_event_id", "child_id"),
    )


def downgrade() -> None:
    op.drop_table("rsvps")
    op.drop_table("school_event_rooms")
    op.drop_table("school_events")
