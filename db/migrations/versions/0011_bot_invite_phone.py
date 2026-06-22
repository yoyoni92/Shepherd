"""add phone_number to bot_invite_tokens

Allows an invite to be coupled to a specific phone number so only
the intended recipient can claim it.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bot_invite_tokens", sa.Column("phone_number", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bot_invite_tokens", "phone_number")
