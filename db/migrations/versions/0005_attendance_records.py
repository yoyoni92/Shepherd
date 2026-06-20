"""add attendance_records (drivers as employees)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-20

One clock-in/out row per (driver, work_date). The admin console reads a month,
generates the weekday skeleton client-side, and overlays these stored records.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE attendance_status_enum AS ENUM ('present', 'late', 'leave', 'absent')")
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.driver_id"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("clock_in", sa.Text(), nullable=True),
        sa.Column("clock_out", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("present", "late", "leave", "absent", name="attendance_status_enum", create_type=False),
            server_default="present",
            nullable=False,
        ),
        sa.UniqueConstraint("driver_id", "work_date", name="uq_attendance_driver_date"),
    )


def downgrade() -> None:
    op.drop_table("attendance_records")
    op.execute("DROP TYPE attendance_status_enum")
