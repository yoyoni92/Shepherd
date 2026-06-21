"""admin-managed maintenance_types catalog

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-21

Replaces the hardcoded maintenance cycle enums with an admin-curated catalog.
Each maintenance_type holds an ordered list of step labels + a km interval; vehicles
reference one via FK. The per-step enums become free text (step labels).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "maintenance_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("interval_km", sa.Integer(), nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # per-step enum columns -> free text (hold any step label)
    op.execute("ALTER TABLE vehicle_care ALTER COLUMN maintenance_type TYPE text USING maintenance_type::text")
    op.execute("ALTER TABLE vehicles ALTER COLUMN last_maintenance_type TYPE text USING last_maintenance_type::text")
    op.execute("ALTER TABLE vehicles ALTER COLUMN next_maintenance_type TYPE text USING next_maintenance_type::text")

    # cycle enum column -> FK into the catalog
    op.drop_column("vehicles", "maintenance_type")
    op.add_column(
        "vehicles",
        sa.Column("maintenance_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("maintenance_types.id"), nullable=True),
    )

    op.execute("DROP TYPE IF EXISTS maintenance_type_enum")
    op.execute("DROP TYPE IF EXISTS last_maintenance_type_enum")


def downgrade() -> None:
    op.execute("CREATE TYPE maintenance_type_enum AS ENUM ('1_small_then_1_big', '2_small_then_1_big')")
    op.execute("CREATE TYPE last_maintenance_type_enum AS ENUM ('small', 'small_1', 'small_2', 'big')")

    op.drop_column("vehicles", "maintenance_type_id")
    op.add_column(
        "vehicles",
        sa.Column("maintenance_type", postgresql.ENUM(name="maintenance_type_enum", create_type=False), nullable=True),
    )
    op.execute(
        "ALTER TABLE vehicles ALTER COLUMN last_maintenance_type TYPE last_maintenance_type_enum "
        "USING last_maintenance_type::last_maintenance_type_enum"
    )
    op.execute(
        "ALTER TABLE vehicles ALTER COLUMN next_maintenance_type TYPE last_maintenance_type_enum "
        "USING next_maintenance_type::last_maintenance_type_enum"
    )
    op.execute(
        "ALTER TABLE vehicle_care ALTER COLUMN maintenance_type TYPE last_maintenance_type_enum "
        "USING maintenance_type::last_maintenance_type_enum"
    )

    op.drop_table("maintenance_types")
