"""Provider-failure resilience: a Fleet/LLM/Drive outage must degrade to a Hebrew
message, never a silent dead chat or a false success. (QA finding G6 / ERR-1/2.)"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
from app import stt, texts
from app.router import dispatch

from tests.conftest import FLEET, whoami_response


def sent_texts(bot) -> list[str]:
    return [c.args[1] for c in bot.send_message.call_args_list]


def dice_count(bot) -> int:
    return bot.send_dice.call_count


async def test_flow_exception_sends_generic_error(store, bot, fleet, mock_api):
    # Fleet is unreachable when a driver taps clock-in.
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", driver_id="d1"))
    mock_api.post(f"{FLEET}/attendance/clock-in").mock(side_effect=httpx.ConnectError("down"))

    await dispatch(
        {"chat_id": 5, "sender_id": 5, "is_callback": True, "callback_data": "clock_in"},
        bot,
        fleet,
    )

    # The user is told something went wrong instead of getting nothing.
    assert texts.GENERIC_ERROR in sent_texts(bot)
    assert dice_count(bot) == 0


async def test_accident_stt_failure_keeps_step_and_offers_text(
    store, bot, fleet, mock_api, monkeypatch
):
    # Whisper fails mid-accident, after the driver already shared safe/location.
    monkeypatch.setattr(stt, "transcribe", AsyncMock(side_effect=RuntimeError("stt down")))
    store[9] = {
        "flow": "accident",
        "step": "awaiting_description",
        "vehicle_id": "v1",
        "datetime": "2026-06-24T10:00:00",
        "attachments": [],
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))

    await dispatch({"chat_id": 9, "sender_id": 9, "voice_id": "vid"}, bot, fleet)

    # A specific message that tells the driver they can retry or type instead.
    assert texts.ACCIDENT_STT_FAILED in sent_texts(bot)
    # The already-captured progress is not lost: still on the description step.
    assert store[9]["step"] == "awaiting_description"
