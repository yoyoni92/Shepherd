"""Test fixtures: in-memory bot_sessions, a fake aiogram Bot, and a Fleet client."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from app import sessions
from app.fleet import FleetClient
from shepherd_config import get_config

FLEET = "http://fleet-api:8000"


@pytest.fixture(autouse=True)
def _reset_config_overlay():
    """Restore the two overlaid config fields and clear LRU cache after each test.

    Tests that call importlib.reload(app.config) create a new settings object;
    this fixture ensures subsequent tests see the original default values.
    """
    import app.config as _config

    saved_db = _config.settings.database_url
    saved_fleet = _config.settings.fleet_api_url
    yield
    get_config.cache_clear()
    _config.settings.database_url = saved_db
    _config.settings.fleet_api_url = saved_fleet


@pytest.fixture
def store(monkeypatch):
    data: dict[int, dict] = {}

    async def get_state(chat_id):
        return dict(data.get(chat_id, {}))

    async def set_state(chat_id, state):
        # Mirror prod: a sticky impersonation context survives flow-state writes.
        if "impersonation" not in state and "impersonation" in data.get(chat_id, {}):
            state = {**state, "impersonation": data[chat_id]["impersonation"]}
        data[chat_id] = dict(state)

    async def clear_state(chat_id):
        imp = data.get(chat_id, {}).get("impersonation")
        if imp is not None:
            data[chat_id] = {"impersonation": imp}
        else:
            data.pop(chat_id, None)

    async def exit_impersonation(chat_id):
        data.pop(chat_id, None)

    monkeypatch.setattr(sessions, "get_state", get_state)
    monkeypatch.setattr(sessions, "set_state", set_state)
    monkeypatch.setattr(sessions, "clear_state", clear_state)
    monkeypatch.setattr(sessions, "exit_impersonation", exit_impersonation)
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


COMPANY_ID = "00000000-0000-0000-0000-0000000000c0"


def whoami_response(
    role: str,
    driver_id: str | None = None,
    company_id: str = COMPANY_ID,
    attendance_enabled: bool = True,
):
    return httpx.Response(
        200,
        json={
            "role": role,
            "driver_id": driver_id,
            "driver_name": "דני",
            "user_id": "u1",
            "company_id": company_id,
            "attendance_enabled": attendance_enabled,
        },
    )
