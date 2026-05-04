"""one register row per child and day

Revision ID: 0014
Revises: 0013
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the earliest row of any duplicates before adding the constraint.
    op.execute(
        """
        DELETE FROM attendance a USING attendance b
        WHERE a.child_id = b.child_id AND a.day = b.day AND a.id > b.id
        """
    )
    op.create_unique_constraint("uq_attendance_child_day", "attendance", ["child_id", "day"])


def downgrade() -> None:
    op.drop_constraint("uq_attendance_child_day", "attendance")
