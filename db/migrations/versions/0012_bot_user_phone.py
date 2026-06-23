"""add phone_number to users

Persists the verified phone a bot user claimed with, so it can be shown
in the admin bot-users view regardless of driver linkage.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone_number")
