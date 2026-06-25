"""Multi-step flow state, persisted in the existing `bot_sessions` table (chat_id -> jsonb).

The bot reaches the DB directly for this one table only (its own conversation state);
everything else goes through Fleet API. Mirrors the n8n session pattern.
"""

from __future__ import annotations

import json
from typing import Any

from psycopg_pool import AsyncConnectionPool

from app.config import settings

_pool: AsyncConnectionPool | None = None


def _dsn() -> str:
    # Strip the SQLAlchemy driver suffix; psycopg wants a plain libpq URL.
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


async def open_pool() -> None:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(_dsn(), min_size=1, max_size=4, open=False)
        await _pool.open()


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_state(chat_id: int) -> dict[str, Any]:
    """Return the stored state dict for a chat ({} when none)."""
    assert _pool is not None, "pool not opened"
    async with _pool.connection() as conn:
        cur = await conn.execute("SELECT state FROM bot_sessions WHERE chat_id = %s", (chat_id,))
        row = await cur.fetchone()
    return row[0] if row and row[0] else {}


async def set_state(chat_id: int, state: dict[str, Any]) -> None:
    """Upsert the full state for a chat."""
    assert _pool is not None, "pool not opened"
    async with _pool.connection() as conn:
        await conn.execute(
            "INSERT INTO bot_sessions (chat_id, state, updated_at) VALUES (%s, %s::jsonb, now()) "
            "ON CONFLICT (chat_id) DO UPDATE SET state = EXCLUDED.state, updated_at = now()",
            (chat_id, json.dumps(state)),
        )


async def clear_state(chat_id: int) -> None:
    assert _pool is not None, "pool not opened"
    async with _pool.connection() as conn:
        await conn.execute("DELETE FROM bot_sessions WHERE chat_id = %s", (chat_id,))
