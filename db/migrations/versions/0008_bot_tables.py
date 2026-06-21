"""add bot_invite_tokens, users, bot_sessions tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_invite_tokens",
        sa.Column("token", sa.Text(), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.driver_id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), server_default=sa.text("now() + INTERVAL '7 days'"), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(sa.text("CREATE TYPE user_role_enum AS ENUM ('admin', 'driver')"))

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("role", postgresql.ENUM(name="user_role_enum", create_type=False), nullable=False, server_default="driver"),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.driver_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "bot_sessions",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True),
        sa.Column("state", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bot_sessions")
    op.drop_table("users")
    op.drop_table("bot_invite_tokens")
    op.execute(sa.text("DROP TYPE IF EXISTS user_role_enum"))
