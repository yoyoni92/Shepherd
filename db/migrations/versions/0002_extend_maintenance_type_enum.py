"""extend last_maintenance_type_enum with small_1 and small_2

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-17
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(__import__("sqlalchemy").text(
        "ALTER TYPE last_maintenance_type_enum ADD VALUE IF NOT EXISTS 'small_1'"
    ))
    op.get_bind().execute(__import__("sqlalchemy").text(
        "ALTER TYPE last_maintenance_type_enum ADD VALUE IF NOT EXISTS 'small_2'"
    ))


def downgrade():
    # Postgres does not support removing enum values; remove and recreate without them.
    op.get_bind().execute(__import__("sqlalchemy").text("""
        ALTER TABLE vehicles
            ALTER COLUMN last_maintenance_type TYPE text,
            ALTER COLUMN next_maintenance_type TYPE text;
        ALTER TABLE vehicle_care
            ALTER COLUMN maintenance_type TYPE text;
        DROP TYPE last_maintenance_type_enum;
        CREATE TYPE last_maintenance_type_enum AS ENUM ('small', 'big');
        ALTER TABLE vehicles
            ALTER COLUMN last_maintenance_type
                TYPE last_maintenance_type_enum
                USING last_maintenance_type::last_maintenance_type_enum,
            ALTER COLUMN next_maintenance_type
                TYPE last_maintenance_type_enum
                USING next_maintenance_type::last_maintenance_type_enum;
        ALTER TABLE vehicle_care
            ALTER COLUMN maintenance_type
                TYPE last_maintenance_type_enum
                USING maintenance_type::last_maintenance_type_enum;
    """))
