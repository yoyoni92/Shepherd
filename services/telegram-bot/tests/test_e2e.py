"""End-to-end tests: one user per role, driving real Telegram updates through the real
dispatcher (`app.main`) with the Telegram Bot API mocked at the session boundary and Fleet
API mocked with respx. These exercise the full pipeline - normalize -> whoami -> router ->
flow -> Telegram I/O - the way Telegram itself would, covering every bot activity.

`tests/test_flows.py` unit-tests flows by calling `dispatch()` directly; this suite is the
black-box counterpart that also exercises `app.main`'s update normalization and aiogram
routing.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import httpx
import pytest
from aiogram import Bot
from app import main, storage, stt, texts, vision
from app.fleet import FleetClient

from tests.conftest import FLEET, whoami_response
from tests.sim import TOKEN, Recorder, TelegramSim

# Distinct chats so a role is unambiguous per scenario ("one user per type").
DRIVER_CHAT = 1001
ADMIN_CHAT = 2001
UNKNOWN_CHAT = 3001

_MONTH = datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m")


@pytest.fixture
def rec() -> Recorder:
    return Recorder()


@pytest.fixture
def sim(rec, store, monkeypatch):
    """A booted bot wired to the real dispatcher, mocked transport, and a mock-Fleet client."""
    bot = Bot(TOKEN, session=rec)
    monkeypatch.setattr(main, "_fleet", FleetClient(base_url=FLEET, token="t"))
    return TelegramSim(bot, rec, main.dp)


def body_of(route) -> dict:
    return json.loads(route.calls.last.request.content)


def _async(return_value) -> AsyncMock:
    """An async stand-in for an external boundary (S3 upload, Whisper, Gemini vision)."""
    return AsyncMock(return_value=return_value)


def as_driver(mock_api, chat_id: int = DRIVER_CHAT, driver_id: str = "d1") -> None:
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", driver_id))


def as_admin(mock_api, chat_id: int = ADMIN_CHAT) -> None:
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))


def as_unknown(mock_api) -> None:
    mock_api.get(f"{FLEET}/whoami").mock(return_value=httpx.Response(404, json={}))


# ============================ Unknown user: enrollment ============================


async def test_unknown_typed_text_nudged_to_button(sim, rec, mock_api):
    # Typing (instead of tapping the share button) nudges to the button - no loop.
    as_unknown(mock_api)
    await sim.text(UNKNOWN_CHAT, "0528588058")
    assert texts.CLAIM_USE_BUTTON in rec.sent_texts()


async def test_unknown_shares_contact_enrolls_as_driver(sim, rec, mock_api):
    as_unknown(mock_api)
    route = mock_api.post(f"{FLEET}/bot-enroll").mock(
        return_value=httpx.Response(200, json={"role": "driver", "driver_id": "d1"})
    )
    await sim.share_contact(UNKNOWN_CHAT, "0501234567")
    assert body_of(route) == {"telegram_chat_id": UNKNOWN_CHAT, "phone_number": "0501234567"}
    assert texts.WELCOME_DRIVER in rec.sent_texts()
    assert rec.of("SetMyCommands")  # role command menu installed


async def test_unknown_shares_contact_enrolls_as_admin(sim, rec, mock_api):
    as_unknown(mock_api)
    mock_api.post(f"{FLEET}/bot-enroll").mock(
        return_value=httpx.Response(200, json={"role": "admin"})
    )
    await sim.share_contact(UNKNOWN_CHAT, "0500000001")
    assert texts.WELCOME_ADMIN in rec.sent_texts()


async def test_unknown_shares_contact_not_authorized(sim, rec, mock_api):
    as_unknown(mock_api)
    mock_api.post(f"{FLEET}/bot-enroll").mock(
        return_value=httpx.Response(404, json={"detail": "not_authorized"})
    )
    await sim.share_contact(UNKNOWN_CHAT, "0509999999")
    assert texts.NOT_AUTHORIZED in rec.sent_texts()


# ============================ Driver user ============================


async def test_driver_text_shows_driver_menu(sim, rec, mock_api):
    as_driver(mock_api)
    await sim.text(DRIVER_CHAT, "hi")
    assert texts.DRIVER_MENU_TITLE in rec.sent_texts()
    assert rec.of("SetMyCommands")


async def test_driver_clock_in_button(sim, rec, mock_api):
    as_driver(mock_api)
    route = mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "08:00"})
    )
    await sim.tap(DRIVER_CHAT, "clock_in")
    assert body_of(route) == {"driver_id": "d1"}
    assert texts.CLOCK_IN_OK.format(time="08:00") in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_driver_clock_in_command(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "07:30"})
    )
    await sim.command(DRIVER_CHAT, "clock_in")
    assert texts.CLOCK_IN_OK.format(time="07:30") in rec.sent_texts()


async def test_driver_clock_out(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.post(f"{FLEET}/attendance/clock-out").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "17:00", "hours": "9.0"})
    )
    await sim.tap(DRIVER_CHAT, "clock_out")
    assert texts.CLOCK_OUT_OK.format(time="17:00", hours="9.0") in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_driver_clock_blocked_no_dice(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(
            200, json={"result": "blocked", "window_start": "06:00", "window_end": "10:00"}
        )
    )
    await sim.tap(DRIVER_CHAT, "clock_in")
    assert texts.CLOCK_BLOCKED.format(start="06:00", end="10:00") in rec.sent_texts()
    assert rec.dice_count() == 0


async def test_driver_vehicle_issue_end_to_end(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(200, json=[{"vehicle_id": "v1"}])
    )
    route = mock_api.post(f"{FLEET}/events").mock(
        return_value=httpx.Response(201, json={"event_id": "e1"})
    )
    await sim.tap(DRIVER_CHAT, "vehicle_issue")
    assert texts.VEHICLE_ISSUE_PROMPT in rec.sent_texts()
    await sim.text(DRIVER_CHAT, "הבלם לא עובד")
    sent = body_of(route)
    assert sent["vehicle_id"] == "v1"
    assert "הבלם לא עובד" in sent["message"]
    assert texts.VEHICLE_ISSUE_DONE in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_driver_update_details_invalid_then_valid(sim, rec, mock_api):
    as_driver(mock_api)
    route = mock_api.patch(f"{FLEET}/drivers/d1").mock(
        return_value=httpx.Response(200, json={"driver_id": "d1"})
    )
    await sim.tap(DRIVER_CHAT, "update_details")
    assert texts.UPDATE_FIELD_MENU in rec.sent_texts()
    await sim.tap(DRIVER_CHAT, "ud_phone")
    assert texts.UPDATE_VALUE_PHONE in rec.sent_texts()
    await sim.text(DRIVER_CHAT, "not-a-phone")
    assert texts.UPDATE_INVALID_PHONE in rec.sent_texts()
    assert not route.called  # rejected, no write
    await sim.text(DRIVER_CHAT, "0501234567")
    assert body_of(route) == {"phone_number": "0501234567"}
    assert texts.UPDATE_DETAILS_DONE in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_driver_attendance_csv_document(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.get(f"{FLEET}/attendance/{_MONTH}").mock(
        return_value=httpx.Response(
            200, json=[{"work_date": "2026-06-01", "clock_in": "08:00", "clock_out": "17:00"}]
        )
    )
    await sim.tap(DRIVER_CHAT, "attendance_csv")
    docs = rec.documents()
    assert len(docs) == 1
    _year, _mon = (int(x) for x in _MONTH.split("-"))
    assert docs[0].document.filename == texts.ATTENDANCE_CSV_FILENAME.format(
        month=texts.HEB_MONTHS[_mon - 1], year=_year
    )


async def test_driver_attendance_csv_empty(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.get(f"{FLEET}/attendance/{_MONTH}").mock(return_value=httpx.Response(200, json=[]))
    await sim.tap(DRIVER_CHAT, "attendance_csv")
    assert texts.ATTENDANCE_EMPTY in rec.sent_texts()
    assert not rec.documents()


async def test_driver_my_vehicle_card(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "vehicle_id": "v1",
                    "vendor": "Toyota",
                    "model": "Corolla",
                    "licensing_plate": "12-345-67",
                    "vehicle_type": "sedan",
                    "current_km": 42000,
                }
            ],
        )
    )
    await sim.tap(DRIVER_CHAT, "my_vehicle")
    card = next(t for t in rec.sent_texts() if texts.MY_VEHICLE_TITLE in t)
    assert "Toyota" in card and "12-345-67" in card and "42000" in card


async def test_driver_my_vehicle_none(sim, rec, mock_api):
    as_driver(mock_api)
    mock_api.get(f"{FLEET}/vehicles").mock(return_value=httpx.Response(200, json=[]))
    await sim.tap(DRIVER_CHAT, "my_vehicle")
    assert texts.NO_VEHICLE in rec.sent_texts()


async def test_driver_blocked_from_admin_feature(sim, rec, mock_api):
    as_driver(mock_api)
    await sim.tap(DRIVER_CHAT, "admin_attendance")
    assert rec.sent_texts() == [texts.ACCESS_DENIED]


async def test_driver_accident_full_wizard(sim, rec, mock_api, monkeypatch):
    as_driver(mock_api)
    monkeypatch.setattr(storage, "upload", _async(return_value="s3://obj"))
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(200, json=[{"vehicle_id": "v1"}])
    )
    accident = mock_api.post(f"{FLEET}/accidents").mock(
        return_value=httpx.Response(201, json={"accident_id": "a1"})
    )
    admins = mock_api.get(f"{FLEET}/users").mock(
        return_value=httpx.Response(200, json=[{"telegram_chat_id": 9999}])
    )

    await sim.tap(DRIVER_CHAT, "accident_start")
    assert texts.ACCIDENT_SAFE_PROMPT in rec.sent_texts()
    await sim.tap(DRIVER_CHAT, "accident_safe")
    await sim.text(DRIVER_CHAT, "פגעתי בעמוד")  # description via text
    await sim.tap(DRIVER_CHAT, "accident_road_clear")
    await sim.photo(DRIVER_CHAT)  # other driver's insurance
    await sim.photo(DRIVER_CHAT)  # other driver's license
    await sim.photo(DRIVER_CHAT)  # other car's registration
    await sim.video(DRIVER_CHAT)  # scene video
    assert texts.ACCIDENT_VIDEO_RECEIVED in rec.sent_texts()
    await sim.tap(DRIVER_CHAT, "accident_videos_done")  # submit

    sent = body_of(accident)
    assert sent["vehicle_id"] == "v1"
    assert sent["description"] == "פגעתי בעמוד"
    assert len(sent["attachments"]) == 4  # 3 photos + 1 video

    await sim.tap(DRIVER_CHAT, "accident_manager_called")
    assert admins.called
    assert any(texts.ACCIDENT_ADMIN_NOTIFY.split("\n")[0] in t for t in rec.sent_to(9999))
    assert texts.ACCIDENT_COMPLETE in rec.sent_texts()
    assert rec.dice_count() == 0  # accident is deliberately excluded from the flourish


async def test_driver_accident_description_via_voice(sim, rec, mock_api, monkeypatch):
    as_driver(mock_api)
    monkeypatch.setattr(stt, "transcribe", _async(return_value="תיאור קולי"))
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(200, json=[{"vehicle_id": "v1"}])
    )
    await sim.tap(DRIVER_CHAT, "accident_start")
    await sim.tap(DRIVER_CHAT, "accident_safe")
    await sim.voice(DRIVER_CHAT)
    # Whisper transcript becomes the description; flow advances to the road-clear step.
    assert texts.ACCIDENT_ROAD_CLEAR_PROMPT in rec.sent_texts()


# ============================ Admin user ============================


async def test_admin_text_shows_admin_menu(sim, rec, mock_api):
    as_admin(mock_api)
    await sim.text(ADMIN_CHAT, "hi")
    assert texts.ADMIN_MENU_TITLE in rec.sent_texts()


async def test_admin_attendance_today(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/attendance/today").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "driver_name": "דני",
                    "clock_in": "08:00",
                    "clock_out": "17:00",
                    "status": "present",
                }
            ],
        )
    )
    await sim.tap(ADMIN_CHAT, "admin_attendance")
    report = next(t for t in rec.sent_texts() if texts.ATTENDANCE_TODAY_TITLE in t)
    assert "דני" in report and "נוכח" in report


async def test_admin_broadcast_send(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/users").mock(
        return_value=httpx.Response(
            200, json=[{"telegram_chat_id": 5555}, {"telegram_chat_id": 5556}]
        )
    )
    await sim.tap(ADMIN_CHAT, "admin_broadcast")
    assert texts.BROADCAST_PROMPT in rec.sent_texts()
    await sim.text(ADMIN_CHAT, "הודעה לכולם")
    assert texts.BROADCAST_CONFIRM.format(count=2) in rec.sent_texts()
    await sim.tap(ADMIN_CHAT, "broadcast_confirm")
    assert rec.sent_to(5555) == ["הודעה לכולם"]
    assert rec.sent_to(5556) == ["הודעה לכולם"]
    assert texts.BROADCAST_SENT in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_admin_broadcast_cancel(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/users").mock(
        return_value=httpx.Response(200, json=[{"telegram_chat_id": 5555}])
    )
    await sim.tap(ADMIN_CHAT, "admin_broadcast")
    await sim.text(ADMIN_CHAT, "טיוטה")
    await sim.tap(ADMIN_CHAT, "broadcast_cancel")
    assert texts.BROADCAST_CANCELLED in rec.sent_texts()
    assert rec.sent_to(5555) == []  # nothing delivered


async def test_admin_fleet_summary(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/kpi/daily").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "total_km_7d": 1200,
                    "avg_km_per_driver_7d": 300,
                    "maintenance_due_count": 2,
                    "docs_expiring_count": 1,
                }
            ],
        )
    )
    await sim.tap(ADMIN_CHAT, "admin_summary")
    summary = next(t for t in rec.sent_texts() if texts.FLEET_SUMMARY_TITLE in t)
    assert "1200" in summary and "300" in summary


async def test_admin_update_driver_field(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/drivers").mock(
        return_value=httpx.Response(200, json=[{"full_name": "דני", "driver_id": "d9"}])
    )
    route = mock_api.patch(f"{FLEET}/drivers/d9").mock(
        return_value=httpx.Response(200, json={"driver_id": "d9"})
    )
    await sim.tap(ADMIN_CHAT, "admin_update_driver")
    assert texts.UPDATE_DRIVER_PICK in rec.sent_texts()
    await sim.tap(ADMIN_CHAT, "ud2_driver_d9")
    assert texts.UPDATE_FIELD_MENU in rec.sent_texts()
    await sim.tap(ADMIN_CHAT, "ud2_field_phone")
    await sim.text(ADMIN_CHAT, "0507654321")
    assert body_of(route) == {"phone_number": "0507654321"}
    assert texts.UPDATE_DRIVER_DONE in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_admin_update_driver_license_scan(sim, rec, mock_api, monkeypatch):
    as_admin(mock_api)
    monkeypatch.setattr(
        vision,
        "extract",
        _async(return_value={"license_number": "12345", "valid_to": "2030-05-05"}),
    )
    mock_api.get(f"{FLEET}/drivers").mock(
        return_value=httpx.Response(200, json=[{"full_name": "דני", "driver_id": "d9"}])
    )
    route = mock_api.patch(f"{FLEET}/drivers/d9").mock(
        return_value=httpx.Response(200, json={"driver_id": "d9"})
    )
    await sim.tap(ADMIN_CHAT, "admin_update_driver")
    await sim.tap(ADMIN_CHAT, "ud2_driver_d9")
    await sim.tap(ADMIN_CHAT, "ud2_field_license_scan")
    assert texts.UPDATE_DRIVER_SCAN_PROMPT in rec.sent_texts()
    await sim.photo(ADMIN_CHAT)
    assert any("12345" in t for t in rec.sent_texts())  # confirm screen
    await sim.tap(ADMIN_CHAT, "ud2_lic_confirm")
    assert body_of(route) == {"license_number": "12345", "license_valid_to": "2030-05-05"}
    assert texts.UPDATE_DRIVER_DONE in rec.sent_texts()


async def test_admin_maintenance_overdue(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"licensing_plate": "11-111-11", "current_km": 51000, "next_maintenance_km": 50000},
                {"licensing_plate": "22-222-22", "current_km": 10000, "next_maintenance_km": 50000},
            ],
        )
    )
    await sim.tap(ADMIN_CHAT, "admin_maintenance")
    assert texts.MAINT_MENU in rec.sent_texts()
    await sim.tap(ADMIN_CHAT, "maint_overdue")
    overdue = next(t for t in rec.sent_texts() if texts.MAINT_OVERDUE_TITLE in t)
    assert "11-111-11" in overdue and "22-222-22" not in overdue


async def test_admin_maintenance_log(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(
            200, json=[{"vehicle_id": "v1", "licensing_plate": "11-111-11", "nickname": "האוטו"}]
        )
    )
    mock_api.get(f"{FLEET}/maintenance-types").mock(
        return_value=httpx.Response(200, json=[{"name": "החלפת שמן"}])
    )
    route = mock_api.post(f"{FLEET}/vehicle_care").mock(
        return_value=httpx.Response(201, json={"id": "vc1"})
    )
    await sim.tap(ADMIN_CHAT, "admin_maintenance")
    await sim.tap(ADMIN_CHAT, "maint_log")
    await sim.tap(ADMIN_CHAT, "ml_veh_v1")
    await sim.tap(ADMIN_CHAT, "ml_type_החלפת שמן")
    assert texts.MAINT_KM_PROMPT in rec.sent_texts()
    await sim.text(ADMIN_CHAT, "55000")
    sent = body_of(route)
    assert sent["vehicle_id"] == "v1"
    assert sent["maintenance_type"] == "החלפת שמן"
    assert sent["km_at_service"] == 55000
    assert texts.MAINT_LOGGED in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_admin_maintenance_log_invalid_km(sim, rec, mock_api):
    as_admin(mock_api)
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(200, json=[{"vehicle_id": "v1", "licensing_plate": "11"}])
    )
    mock_api.get(f"{FLEET}/maintenance-types").mock(
        return_value=httpx.Response(200, json=[{"name": "שמן"}])
    )
    await sim.tap(ADMIN_CHAT, "admin_maintenance")
    await sim.tap(ADMIN_CHAT, "maint_log")
    await sim.tap(ADMIN_CHAT, "ml_veh_v1")
    await sim.tap(ADMIN_CHAT, "ml_type_שמן")
    await sim.text(ADMIN_CHAT, "abc")
    assert texts.MAINT_KM_INVALID in rec.sent_texts()


async def test_admin_doc_scan_vehicle_license(sim, rec, mock_api, monkeypatch):
    as_admin(mock_api)
    monkeypatch.setattr(storage, "upload", _async(return_value="s3://doc"))
    monkeypatch.setattr(
        vision, "extract", _async(return_value={"plate_number": "55", "valid_to": "2027-02-02"})
    )
    route = mock_api.post(f"{FLEET}/documents/extracted").mock(
        return_value=httpx.Response(200, json={"status": "updated"})
    )
    await sim.tap(ADMIN_CHAT, "doc_scan")
    assert texts.DOC_SCAN_PICK_TYPE in rec.sent_texts()
    await sim.tap(ADMIN_CHAT, "ds_type_vehicle_license")
    assert texts.DOC_SCAN_SEND_FILE in rec.sent_texts()
    await sim.photo(ADMIN_CHAT)
    assert any("55" in t for t in rec.sent_texts())  # confirm screen
    await sim.tap(ADMIN_CHAT, "ds_confirm")
    assert body_of(route) == {
        "doc_type": "license",
        "licensing_plate": "55",
        "license_valid_to": "2027-02-02",
        "license_file_url": "s3://doc",
    }
    assert texts.DOC_SCAN_APPLIED in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_admin_doc_scan_driver_license(sim, rec, mock_api, monkeypatch):
    as_admin(mock_api)
    monkeypatch.setattr(storage, "upload", _async(return_value="s3://doc"))
    monkeypatch.setattr(
        vision,
        "extract",
        _async(return_value={"license_number": "98765", "valid_to": "2031-01-01"}),
    )
    mock_api.get(f"{FLEET}/drivers").mock(
        return_value=httpx.Response(200, json=[{"full_name": "דני", "driver_id": "d9"}])
    )
    route = mock_api.patch(f"{FLEET}/drivers/d9").mock(
        return_value=httpx.Response(200, json={"driver_id": "d9"})
    )
    await sim.tap(ADMIN_CHAT, "doc_scan")
    await sim.tap(ADMIN_CHAT, "ds_type_driver_license")
    assert texts.DOC_SCAN_PICK_DRIVER in rec.sent_texts()
    await sim.tap(ADMIN_CHAT, "ds_drv_d9")
    await sim.photo(ADMIN_CHAT)
    await sim.tap(ADMIN_CHAT, "ds_confirm")
    assert body_of(route) == {"license_number": "98765", "license_valid_to": "2031-01-01"}
    assert texts.DOC_SCAN_APPLIED in rec.sent_texts()


async def test_admin_doc_scan_extraction_failed(sim, rec, mock_api, monkeypatch):
    as_admin(mock_api)
    monkeypatch.setattr(storage, "upload", _async(return_value="s3://doc"))
    monkeypatch.setattr(vision, "extract", _async(return_value={}))
    await sim.tap(ADMIN_CHAT, "doc_scan")
    await sim.tap(ADMIN_CHAT, "ds_type_insurance")
    await sim.photo(ADMIN_CHAT)
    assert texts.DOC_SCAN_FAILED in rec.sent_texts()


async def test_admin_doc_scan_cancel(sim, rec, mock_api, monkeypatch):
    as_admin(mock_api)
    monkeypatch.setattr(storage, "upload", _async(return_value="s3://doc"))
    monkeypatch.setattr(
        vision, "extract", _async(return_value={"plate_number": "77", "valid_to": "2028-08-08"})
    )
    await sim.tap(ADMIN_CHAT, "doc_scan")
    await sim.tap(ADMIN_CHAT, "ds_type_insurance")
    await sim.photo(ADMIN_CHAT)  # reach the confirm screen, where cancel is offered
    await sim.tap(ADMIN_CHAT, "ds_cancel")
    assert texts.DOC_SCAN_CANCELLED in rec.sent_texts()
