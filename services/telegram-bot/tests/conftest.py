"""Test fixtures: in-memory bot_sessions, a fake aiogram Bot, and a Fleet client."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from app import sessions
from app.fleet import FleetClient

FLEET = "http://fleet-api:8000"


@pytest.fixture
def store(monkeypatch):
    data: dict[int, dict] = {}

    async def get_state(chat_id):
        return dict(data.get(chat_id, {}))

    async def set_state(chat_id, state):
        data[chat_id] = dict(state)

    async def clear_state(chat_id):
        data.pop(chat_id, None)

    monkeypatch.setattr(sessions, "get_state", get_state)
    monkeypatch.setattr(sessions, "set_state", set_state)
    monkeypatch.setattr(sessions, "clear_state", clear_state)
    return data


@pytest.fixture
def bot():
    b = AsyncMock()
    file_obj = type("F", (), {"file_path": "path/to/file"})()
    b.get_file = AsyncMock(return_value=file_obj)
    b.download_file = AsyncMock(side_effect=lambda *a, **k: io.BytesIO(b"rawbytes"))
    return b


@pytest.fixture
def fleet():
    return FleetClient(base_url=FLEET, token="t")


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as router:
        yield router


def whoami_response(role: str, driver_id: str | None = None):
    return httpx.Response(
        200,
        json={
            "role": role,
            "driver_id": driver_id,
            "driver_name": "דני",
            "user_id": "u1",
        },
    )
