"""extend accident_attachment_category_enum with two new values

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.get_bind().execute(sa.text(
        "ALTER TYPE accident_attachment_category_enum ADD VALUE IF NOT EXISTS 'another_driver_license'"
    ))
    op.get_bind().execute(sa.text(
        "ALTER TYPE accident_attachment_category_enum ADD VALUE IF NOT EXISTS 'accident_video'"
    ))


def downgrade() -> None:
    # Postgres does not support removing enum values; downgrade is a no-op.
    pass
