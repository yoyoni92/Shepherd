"""add vehicles.vehicle_type enum

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-21

Each vehicle gets a type (motorcycle/car/van/bus/truck). Nullable so existing rows
remain valid; the create form requires it going forward.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE vehicle_type_enum AS ENUM ('motorcycle', 'car', 'van', 'bus', 'truck')")
    op.add_column(
        "vehicles",
        sa.Column(
            "vehicle_type",
            postgresql.ENUM("motorcycle", "car", "van", "bus", "truck", name="vehicle_type_enum", create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("vehicles", "vehicle_type")
    op.execute("DROP TYPE vehicle_type_enum")
