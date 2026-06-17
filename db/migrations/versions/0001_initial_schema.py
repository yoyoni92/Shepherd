"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Enum type SQL definitions
# Using op.execute so SQLAlchemy does not auto-manage the types.
# ---------------------------------------------------------------------------

_ENUM_SQLS = [
    "CREATE TYPE allowed_driver_enum AS ENUM ('all_drivers', 'specific_driver_only')",
    "CREATE TYPE maintenance_type_enum AS ENUM ('1_small_then_1_big', '2_small_then_1_big')",
    "CREATE TYPE last_maintenance_type_enum AS ENUM ('small', 'big')",
    "CREATE TYPE driver_status_enum AS ENUM ('active', 'inactive')",
    "CREATE TYPE customer_status_enum AS ENUM ('active', 'inactive')",
    "CREATE TYPE km_update_source_enum AS ENUM ('telegram', 'admin_ui')",
    (
        "CREATE TYPE accident_attachment_category_enum AS ENUM ("
        "'another_driver_insurance', 'another_car_registration', "
        "'photo_our_vehicle', 'photo_other_vehicle', 'photo_accident_area')"
    ),
    "CREATE TYPE ticket_type_enum AS ENUM ('traffic', 'parking')",
    (
        "CREATE TYPE report_status_enum AS ENUM "
        "('unpaid', 'paid', 'contested', 'transferred_to_driver')"
    ),
    (
        "CREATE TYPE event_type_enum AS ENUM ("
        "'maintenance_due', 'license_expiring', 'insurance_expiring', "
        "'ticket_received', 'accident_logged')"
    ),
    "CREATE TYPE event_severity_enum AS ENUM ('info', 'warning', 'critical')",
    "CREATE TYPE event_source_type_enum AS ENUM ('km_updates', 'scheduler', 'accidents', 'reports')",
    "CREATE TYPE event_status_enum AS ENUM ('open', 'acknowledged', 'resolved', 'dismissed')",
    "CREATE TYPE channel_enum AS ENUM ('telegram', 'whatsapp', 'webapp')",
    "CREATE TYPE channel_status_enum AS ENUM ('linked', 'revoked')",
]

_DROP_ENUM_SQLS = [
    "DROP TYPE IF EXISTS channel_status_enum",
    "DROP TYPE IF EXISTS channel_enum",
    "DROP TYPE IF EXISTS event_status_enum",
    "DROP TYPE IF EXISTS event_source_type_enum",
    "DROP TYPE IF EXISTS event_severity_enum",
    "DROP TYPE IF EXISTS event_type_enum",
    "DROP TYPE IF EXISTS report_status_enum",
    "DROP TYPE IF EXISTS ticket_type_enum",
    "DROP TYPE IF EXISTS accident_attachment_category_enum",
    "DROP TYPE IF EXISTS km_update_source_enum",
    "DROP TYPE IF EXISTS customer_status_enum",
    "DROP TYPE IF EXISTS driver_status_enum",
    "DROP TYPE IF EXISTS last_maintenance_type_enum",
    "DROP TYPE IF EXISTS maintenance_type_enum",
    "DROP TYPE IF EXISTS allowed_driver_enum",
]


def _e(name: str) -> postgresql.ENUM:
    """Reference an existing PG enum type - create_type=False prevents auto DDL."""
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    # 1. Create all enum types via the live connection to avoid alembic's
    #    empty-params execution path that confuses psycopg3's SQL parser.
    bind = op.get_bind()
    for sql in _ENUM_SQLS:
        bind.execute(sa.text(sql))

    # 2. Create tables in dependency order
    op.create_table(
        "drivers",
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=False),
        sa.Column("license_number", sa.Text(), nullable=True),
        sa.Column("status", _e("driver_status_enum"), server_default="active", nullable=False),
        sa.PrimaryKeyConstraint("driver_id"),
        sa.UniqueConstraint("phone_number"),
    )

    op.create_table(
        "customers",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column(
            "status", _e("customer_status_enum"), server_default="active", nullable=False
        ),
        sa.PrimaryKeyConstraint("customer_id"),
    )

    op.create_table(
        "vehicles",
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("licensing_plate", sa.Text(), nullable=False),
        sa.Column("nickname", sa.Text(), nullable=True),
        sa.Column("inseration_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("insurance_valid_to", sa.Date(), nullable=True),
        sa.Column("license_valid_to", sa.Date(), nullable=True),
        sa.Column("insurance_file_url", sa.Text(), nullable=True),
        sa.Column("registration_file_url", sa.Text(), nullable=True),
        sa.Column("allowed_driver", _e("allowed_driver_enum"), nullable=True),
        sa.Column("vendor", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("last_maintenance_date", sa.Date(), nullable=True),
        sa.Column("last_maintenance_type", _e("last_maintenance_type_enum"), nullable=True),
        sa.Column("last_maintenance_km", sa.Integer(), nullable=True),
        sa.Column("next_maintenance_km", sa.Integer(), nullable=True),
        sa.Column("next_maintenance_type", _e("last_maintenance_type_enum"), nullable=True),
        sa.Column("current_km", sa.Integer(), nullable=True),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.driver_id"),
            nullable=True,
        ),
        sa.Column("maintenance_type", _e("maintenance_type_enum"), nullable=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.customer_id"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("vehicle_id"),
        sa.UniqueConstraint("licensing_plate"),
    )

    op.create_table(
        "accidents",
        sa.Column(
            "accident_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.vehicle_id"),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.driver_id"),
            nullable=True,
        ),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("another_driver_licensing_plate", sa.Text(), nullable=True),
        sa.Column("another_driver_phone_number", sa.Text(), nullable=True),
        sa.Column("another_driver_id_number", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("accident_id"),
    )

    op.create_table(
        "accident_attachments",
        sa.Column(
            "attachment_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "accident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accidents.accident_id"),
            nullable=False,
        ),
        sa.Column(
            "category", _e("accident_attachment_category_enum"), nullable=False
        ),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column(
            "uploaded_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("attachment_id"),
    )

    op.create_table(
        "km_updates",
        sa.Column(
            "km_update_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.vehicle_id"),
            nullable=False,
        ),
        sa.Column("km", sa.Integer(), nullable=False),
        sa.Column(
            "recorded_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.driver_id"),
            nullable=True,
        ),
        sa.Column("source", _e("km_update_source_enum"), nullable=False),
        sa.PrimaryKeyConstraint("km_update_id"),
    )

    op.create_table(
        "vehicle_care",
        sa.Column(
            "care_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.vehicle_id"),
            nullable=False,
        ),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column(
            "maintenance_type", _e("last_maintenance_type_enum"), nullable=False
        ),
        sa.Column("km_at_service", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("garage", sa.Text(), nullable=True),
        sa.Column("invoice_file_url", sa.Text(), nullable=True),
        sa.Column("next_maintenance_km", sa.Integer(), nullable=True),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.driver_id"),
            nullable=True,
        ),
        sa.Column(
            "created_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("care_id"),
    )

    op.create_table(
        "reports",
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.vehicle_id"),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.driver_id"),
            nullable=True,
        ),
        sa.Column("ticket_type", _e("ticket_type_enum"), nullable=False),
        sa.Column("violation_desc", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("issued_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "status", _e("report_status_enum"), server_default="unpaid", nullable=False
        ),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("authority", sa.Text(), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column(
            "created_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("report_id"),
    )

    op.create_table(
        "events",
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.vehicle_id"),
            nullable=True,
        ),
        sa.Column("event_type", _e("event_type_enum"), nullable=False),
        sa.Column("severity", _e("event_severity_enum"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("source_type", _e("event_source_type_enum"), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status", _e("event_status_enum"), server_default="open", nullable=False
        ),
        sa.Column("notified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "triggered_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )

    op.create_table(
        "system_config",
        sa.Column("config_key", sa.Text(), nullable=False),
        sa.Column(
            "config_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("config_key"),
    )

    op.create_table(
        "channel_identities",
        sa.Column(
            "identity_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("channel", _e("channel_enum"), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=False),
        sa.Column(
            "status", _e("channel_status_enum"), server_default="linked", nullable=False
        ),
        sa.Column(
            "linked_ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("identity_id"),
        sa.UniqueConstraint("channel", "external_id"),
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("channel_identities")
    op.drop_table("system_config")
    op.drop_table("events")
    op.drop_table("reports")
    op.drop_table("vehicle_care")
    op.drop_table("km_updates")
    op.drop_table("accident_attachments")
    op.drop_table("accidents")
    op.drop_table("vehicles")
    op.drop_table("customers")
    op.drop_table("drivers")

    # Drop all enum types in reverse creation order
    bind = op.get_bind()
    for sql in _DROP_ENUM_SQLS:
        bind.execute(sa.text(sql))
