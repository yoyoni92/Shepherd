"""add drivers.license_valid_to (nullable)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-20

Driver's licence expiry, distinct from the vehicle's annual רישוי (license_valid_to on
vehicles). Nullable everywhere — the field is optional on the add-driver form and in the API.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("drivers", sa.Column("license_valid_to", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("drivers", "license_valid_to")
