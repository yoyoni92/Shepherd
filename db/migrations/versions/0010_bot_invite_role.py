"""make bot_invite_tokens.driver_id nullable and add role

Lets an admin issue an invite for a standalone (non-driver) bot user and
pre-assign its role. Driver invites still carry driver_id; admin invites
may omit it.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("bot_invite_tokens", "driver_id", nullable=True)
    op.add_column(
        "bot_invite_tokens",
        sa.Column(
            "role",
            postgresql.ENUM(name="user_role_enum", create_type=False),
            nullable=False,
            server_default="driver",
        ),
    )


def downgrade() -> None:
    # Standalone admin invites have no driver; drop them before restoring NOT NULL.
    op.execute(sa.text("DELETE FROM bot_invite_tokens WHERE driver_id IS NULL"))
    op.drop_column("bot_invite_tokens", "role")
    op.alter_column("bot_invite_tokens", "driver_id", nullable=False)
