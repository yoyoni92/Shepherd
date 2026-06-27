"""Flow + router behavior tests (Fleet API mocked via respx, bot + sessions faked)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
from app import storage, stt, texts, vision
from app.router import dispatch

from tests.conftest import COMPANY_ID, FLEET, whoami_response


def sent_texts(bot) -> list[str]:
    return [c.args[1] for c in bot.send_message.call_args_list]


def keyboard_removed(bot) -> bool:
    """True if any send cleared the bottom reply keyboard (ReplyKeyboardRemove)."""
    return any(
        getattr(c.kwargs.get("reply_markup"), "remove_keyboard", False)
        for c in bot.send_message.call_args_list
    )


def menu_callbacks(bot) -> list[str]:
    """Callback strings of the last inline keyboard the bot sent (the role menu)."""
    for call in bot.send_message.call_args_list:
        kb = call.kwargs.get("reply_markup")
        if kb is not None and hasattr(kb, "inline_keyboard"):
            return [b.callback_data for row in kb.inline_keyboard for b in row]
    return []


def caller_ctx(route) -> dict:
    return json.loads(route.calls.last.request.headers["X-Caller-Context"])


def last_body(route) -> dict:
    return json.loads(route.calls.last.request.content)


# --- Router gating ---


async def test_unknown_start_asked_for_phone(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=httpx.Response(404, json={}))
    await dispatch({"chat_id": 1, "sender_id": 1, "is_start": True, "start_token": None}, bot, fleet)
    assert texts.CLAIM_REQUEST_PHONE in sent_texts(bot)


async def test_unknown_typed_number_nudged_to_button(store, bot, fleet, mock_api):
    # Driver typed their number instead of tapping the share button -> nudge, not loop.
    mock_api.get(f"{FLEET}/whoami").mock(return_value=httpx.Response(404, json={}))
    await dispatch({"chat_id": 1, "sender_id": 1, "text": "0528588058"}, bot, fleet)
    assert texts.CLAIM_USE_BUTTON in sent_texts(bot)


async def test_enroll_success_driver(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=httpx.Response(404, json={}))
    route = mock_api.post(f"{FLEET}/bot-enroll").mock(
        return_value=httpx.Response(200, json={"role": "driver", "driver_id": "d1", "user_id": "u1"})
    )
    await dispatch(
        {"chat_id": 2, "sender_id": 2, "contact_phone": "0501234567", "contact_user_id": 2}, bot, fleet
    )
    assert last_body(route) == {"telegram_chat_id": 2, "phone_number": "0501234567"}
    assert texts.WELCOME_DRIVER in sent_texts(bot)
    bot.set_my_commands.assert_awaited()


async def test_enroll_not_authorized(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=httpx.Response(404, json={}))
    mock_api.post(f"{FLEET}/bot-enroll").mock(
        return_value=httpx.Response(404, json={"detail": "not_authorized"})
    )
    await dispatch(
        {"chat_id": 3, "sender_id": 3, "contact_phone": "0500000000", "contact_user_id": 3}, bot, fleet
    )
    assert texts.NOT_AUTHORIZED in sent_texts(bot)


async def test_driver_gets_driver_menu(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    await dispatch({"chat_id": 3, "sender_id": 3, "text": "hi"}, bot, fleet)
    assert texts.DRIVER_MENU_TITLE in sent_texts(bot)


async def test_driver_blocked_from_admin_feature(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    await dispatch(
        {"chat_id": 4, "sender_id": 4, "is_callback": True, "callback_data": "admin_attendance"},
        bot,
        fleet,
    )
    assert sent_texts(bot) == [texts.ACCESS_DENIED]


# --- Driver flows ---


async def test_clock_in(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    route = mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "08:00"})
    )
    await dispatch(
        {"chat_id": 5, "sender_id": 5, "is_callback": True, "callback_data": "clock_in"}, bot, fleet
    )
    assert last_body(route) == {"driver_id": "d1"}
    assert texts.CLOCK_IN_OK.format(time="08:00") in sent_texts(bot)


# --- Attendance feature flag (F5): clock gated by the company flag ---


async def test_driver_menu_hides_clock_when_attendance_disabled(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(
        return_value=whoami_response("driver", "d1", attendance_enabled=False)
    )
    await dispatch({"chat_id": 50, "sender_id": 50, "text": "hi"}, bot, fleet)
    cbs = menu_callbacks(bot)
    assert "clock_in" not in cbs and "clock_out" not in cbs
    assert "vehicle_issue" in cbs  # the rest of the menu is unaffected


async def test_driver_menu_shows_clock_when_attendance_enabled(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(
        return_value=whoami_response("driver", "d1", attendance_enabled=True)
    )
    await dispatch({"chat_id": 51, "sender_id": 51, "text": "hi"}, bot, fleet)
    cbs = menu_callbacks(bot)
    assert "clock_in" in cbs and "clock_out" in cbs


async def test_clock_denied_when_attendance_disabled(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(
        return_value=whoami_response("driver", "d1", attendance_enabled=False)
    )
    route = mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "08:00"})
    )
    await dispatch(
        {"chat_id": 52, "sender_id": 52, "is_callback": True, "callback_data": "clock_in"},
        bot,
        fleet,
    )
    assert texts.ATTENDANCE_DISABLED in sent_texts(bot)
    assert not route.called  # the API is never hit when the flag is off


async def test_storage_upload_sends_company_caller_context(mock_api):
    from app.config import settings

    route = mock_api.post(f"{settings.fleet_api_url.rstrip('/')}/files").mock(
        return_value=httpx.Response(200, json={"file_url": "https://drive/x"})
    )
    url = await storage.upload("accidents/1/a.jpg", b"bytes", "image/jpeg", company_id="c0")
    assert url == "https://drive/x"
    headers = route.calls.last.request.headers
    assert json.loads(headers["X-Caller-Context"]) == {"role": "admin", "company_id": "c0"}
    assert headers["X-Internal-Token"]


async def test_vehicle_issue_logs_event(store, bot, fleet, mock_api):
    store[7] = {"flow": "vehicle_issue", "step": "awaiting_description"}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(200, json=[{"vehicle_id": "v1"}])
    )
    route = mock_api.post(f"{FLEET}/events").mock(
        return_value=httpx.Response(201, json={"event_id": "e1"})
    )
    await dispatch({"chat_id": 7, "sender_id": 7, "text": "הבלם לא עובד"}, bot, fleet)
    body = last_body(route)
    assert body["vehicle_id"] == "v1"
    assert "הבלם לא עובד" in body["message"]
    assert 7 not in store  # session cleared


async def test_flow_call_carries_company_id(store, bot, fleet, mock_api):
    """The per-update client is company-bound: every downstream caller-context is scoped."""
    store[7] = {"flow": "vehicle_issue", "step": "awaiting_description"}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    veh = mock_api.get(f"{FLEET}/vehicles").mock(
        return_value=httpx.Response(200, json=[{"vehicle_id": "v1"}])
    )
    events = mock_api.post(f"{FLEET}/events").mock(
        return_value=httpx.Response(201, json={"event_id": "e1"})
    )
    await dispatch({"chat_id": 7, "sender_id": 7, "text": "הבלם לא עובד"}, bot, fleet)
    # Driver-scoped read and admin-scoped write both carry the enrolled user's company.
    assert caller_ctx(veh) == {"role": "driver", "driver_id": "d1", "company_id": COMPANY_ID}
    assert caller_ctx(events)["company_id"] == COMPANY_ID


# --- Accident: voice and text both fill description; submit posts it ---


async def test_accident_safe_requests_location_then_stores_it(store, bot, fleet, mock_api):
    store[7] = {
        "flow": "accident",
        "step": "awaiting_safe",
        "vehicle_id": "v1",
        "datetime": "2026-06-24T10:00:00",
        "attachments": [],
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    # Confirming safety advances to the location step (not straight to the description).
    await dispatch(
        {"chat_id": 7, "sender_id": 7, "is_callback": True, "callback_data": "accident_safe"},
        bot,
        fleet,
    )
    assert store[7]["step"] == "awaiting_location"
    # Sharing the location stores "lat,lon" and advances to the description step.
    await dispatch(
        {"chat_id": 7, "sender_id": 7, "location_lat": 32.0853, "location_lon": 34.7818},
        bot,
        fleet,
    )
    assert store[7]["location"] == "32.0853,34.7818"
    assert store[7]["step"] == "awaiting_description"
    # The share-location reply keyboard is cleared once the location is in.
    assert keyboard_removed(bot)


async def test_accident_description_via_text(store, bot, fleet, mock_api):
    store[8] = {
        "flow": "accident",
        "step": "awaiting_description",
        "vehicle_id": "v1",
        "datetime": "2026-06-24T10:00:00",
        "attachments": [],
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    await dispatch({"chat_id": 8, "sender_id": 8, "text": "פגעתי בעמוד"}, bot, fleet)
    assert store[8]["description"] == "פגעתי בעמוד"
    assert store[8]["step"] == "awaiting_road_clear"


async def test_accident_description_via_voice(store, bot, fleet, mock_api, monkeypatch):
    monkeypatch.setattr(stt, "transcribe", AsyncMock(return_value="תיאור קולי"))
    store[9] = {
        "flow": "accident",
        "step": "awaiting_description",
        "vehicle_id": "v1",
        "datetime": "2026-06-24T10:00:00",
        "attachments": [],
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    await dispatch({"chat_id": 9, "sender_id": 9, "voice_id": "vid"}, bot, fleet)
    assert store[9]["description"] == "תיאור קולי"


async def test_accident_submit_posts_description_and_attachments(store, bot, fleet, mock_api):
    store[10] = {
        "flow": "accident",
        "step": "awaiting_area_videos",
        "vehicle_id": "v1",
        "datetime": "2026-06-24T10:00:00",
        "description": "desc",
        "attachments": [{"category": "another_driver_insurance", "file_url": "u"}],
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    route = mock_api.post(f"{FLEET}/accidents").mock(
        return_value=httpx.Response(201, json={"accident_id": "a1"})
    )
    await dispatch(
        {
            "chat_id": 10,
            "sender_id": 10,
            "is_callback": True,
            "callback_data": "accident_videos_done",
        },
        bot,
        fleet,
    )
    body = last_body(route)
    assert body["description"] == "desc"
    assert body["vehicle_id"] == "v1"
    assert len(body["attachments"]) == 1
    assert store[10]["step"] == "awaiting_manager_call"


# --- Admin doc scan (vision) ---


async def test_doc_scan_file_extracts_and_confirms(store, bot, fleet, mock_api, monkeypatch):
    monkeypatch.setattr(
        vision, "extract", AsyncMock(return_value={"plate_number": "55", "valid_to": "2027-02-02"})
    )
    monkeypatch.setattr(storage, "upload", AsyncMock(return_value="https://drive/url"))
    store[11] = {"flow": "doc_scan", "step": "awaiting_file", "doc_type": "vehicle_license"}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))
    await dispatch({"chat_id": 11, "sender_id": 11, "photo_id": "pid"}, bot, fleet)
    assert store[11]["step"] == "awaiting_confirm"
    assert store[11]["fields"] == {"plate_number": "55", "valid_to": "2027-02-02"}
    assert any("55" in t for t in sent_texts(bot))


async def test_doc_scan_confirm_applies_insurance(store, bot, fleet, mock_api):
    store[12] = {
        "flow": "doc_scan",
        "step": "awaiting_confirm",
        "doc_type": "insurance",
        "fields": {"plate_number": "123", "valid_to": "2026-01-01"},
        "file_url": "u",
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))
    route = mock_api.post(f"{FLEET}/documents/extracted").mock(
        return_value=httpx.Response(200, json={"status": "updated"})
    )
    await dispatch(
        {"chat_id": 12, "sender_id": 12, "is_callback": True, "callback_data": "ds_confirm"},
        bot,
        fleet,
    )
    body = last_body(route)
    assert body == {
        "doc_type": "insurance",
        "licensing_plate": "123",
        "insurance_valid_to": "2026-01-01",
        "insurance_file_url": "u",
    }
    assert texts.DOC_SCAN_APPLIED in sent_texts(bot)
    assert 12 not in store


async def test_doc_scan_cancel_discards(store, bot, fleet, mock_api):
    store[13] = {
        "flow": "doc_scan",
        "step": "awaiting_confirm",
        "doc_type": "insurance",
        "fields": {},
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))
    await dispatch(
        {"chat_id": 13, "sender_id": 13, "is_callback": True, "callback_data": "ds_cancel"},
        bot,
        fleet,
    )
    assert 13 not in store
    assert texts.DOC_SCAN_CANCELLED in sent_texts(bot)


# --- Command menu (the ☰ button) ---


async def test_command_routes_to_feature(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    route = mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "07:30"})
    )
    await dispatch({"chat_id": 20, "sender_id": 20, "command": "clock_in"}, bot, fleet)
    assert route.called
    assert texts.CLOCK_IN_OK.format(time="07:30") in sent_texts(bot)


async def test_menu_command_sets_commands_and_shows_menu(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))
    await dispatch({"chat_id": 21, "sender_id": 21, "command": "menu"}, bot, fleet)
    bot.set_my_commands.assert_awaited()
    assert texts.ADMIN_MENU_TITLE in sent_texts(bot)


# --- Animated-emoji (sendDice) flourish ---


async def test_dice_on_clock_in_success(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "08:00"})
    )
    await dispatch({"chat_id": 30, "sender_id": 30, "command": "clock_in"}, bot, fleet)
    bot.send_dice.assert_awaited_once()


async def test_no_dice_when_already_clocked_in(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("driver", "d1"))
    mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "already_in"})
    )
    await dispatch({"chat_id": 31, "sender_id": 31, "command": "clock_in"}, bot, fleet)
    bot.send_dice.assert_not_awaited()


# --- Update driver: scan license via vision ---


async def test_update_driver_license_scan_extracts_and_confirms(
    store, bot, fleet, mock_api, monkeypatch
):
    monkeypatch.setattr(
        vision,
        "extract",
        AsyncMock(return_value={"license_number": "12345", "valid_to": "2030-05-05"}),
    )
    store[40] = {"flow": "update_driver", "step": "awaiting_license_file", "target_driver_id": "d9"}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))
    await dispatch({"chat_id": 40, "sender_id": 40, "photo_id": "pid"}, bot, fleet)
    assert store[40]["step"] == "awaiting_license_confirm"
    assert store[40]["lic_fields"] == {"license_number": "12345", "valid_to": "2030-05-05"}
    assert any("12345" in t for t in sent_texts(bot))


async def test_update_driver_license_apply_patches_driver(store, bot, fleet, mock_api):
    store[41] = {
        "flow": "update_driver",
        "step": "awaiting_license_confirm",
        "target_driver_id": "d9",
        "lic_fields": {"license_number": "12345", "valid_to": "2030-05-05"},
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=whoami_response("admin"))
    route = mock_api.patch(f"{FLEET}/drivers/d9").mock(
        return_value=httpx.Response(200, json={"driver_id": "d9"})
    )
    await dispatch(
        {"chat_id": 41, "sender_id": 41, "is_callback": True, "callback_data": "ud2_lic_confirm"},
        bot,
        fleet,
    )
    assert last_body(route) == {"license_number": "12345", "license_valid_to": "2030-05-05"}
    assert texts.UPDATE_DRIVER_DONE in sent_texts(bot)
    assert 41 not in store
    bot.send_dice.assert_awaited_once()


# --- Feature 6: System Admin (overview / debug / customer-live impersonation) ---

OPERATOR_ID = "op-1"
LIVE_CO = "00000000-0000-0000-0000-0000000000c9"
PLAYGROUND = "00000000-0000-0000-0000-0000000000aa"


def sysadmin_whoami(playground: str | None = PLAYGROUND) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "role": "admin",
            "driver_id": None,
            "driver_name": None,
            "user_id": OPERATOR_ID,
            "company_id": None,
            "attendance_enabled": False,
            "is_system_admin": True,
            "playground_company_id": playground,
        },
    )


def live_imp(role: str = "admin", **extra) -> dict:
    imp = {
        "mode": "live",
        "role": role,
        "company_id": LIVE_CO,
        "company_name": "Acme",
        "operator_id": OPERATOR_ID,
        "effective_id": "x1",
        "attendance_enabled": True,
    }
    imp.update(extra)
    return imp


async def test_system_admin_menu_shown(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    await dispatch({"chat_id": 60, "sender_id": 60, "text": "hi"}, bot, fleet)
    assert texts.SYSADMIN_MENU_TITLE in sent_texts(bot)
    assert menu_callbacks(bot) == ["sa_overview", "sa_debug", "sa_live"]


async def test_overview_uses_system_admin_context(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    route = mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(
            200,
            json={
                "companies": [
                    {
                        "company_id": LIVE_CO,
                        "name": "Acme",
                        "vehicle_count": 3,
                        "driver_count": 5,
                        "open_event_count": 1,
                        "attendance_enabled": True,
                        "gdrive_configured": False,
                    }
                ]
            },
        )
    )
    await dispatch(
        {"chat_id": 61, "sender_id": 61, "is_callback": True, "callback_data": "sa_overview"},
        bot,
        fleet,
    )
    # The overview reads as the company-less system admin (no company_id, no impersonator).
    assert caller_ctx(route) == {"role": "admin"}
    assert any("Acme" in t for t in sent_texts(bot))


async def test_enter_debug_binds_playground_persona(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    mock_api.get(f"{FLEET}/sysadmin/companies/{PLAYGROUND}/drivers").mock(
        return_value=httpx.Response(200, json=[{"driver_id": "pd1", "full_name": "Playground 1"}])
    )
    audit = mock_api.post(f"{FLEET}/sysadmin/impersonation-audit").mock(
        return_value=httpx.Response(201, json={"status": "ok"})
    )
    await dispatch(
        {"chat_id": 62, "sender_id": 62, "is_callback": True, "callback_data": "sa_dbg_driver"},
        bot,
        fleet,
    )
    imp = store[62]["impersonation"]
    assert imp["mode"] == "debug"
    assert imp["role"] == "driver"
    assert imp["company_id"] == PLAYGROUND
    assert imp["driver_id"] == "pd1"
    assert not audit.called  # Debug is unaudited


async def test_enter_live_sets_context_and_posts_start_audit(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    mock_api.get(f"{FLEET}/sysadmin/companies").mock(
        return_value=httpx.Response(200, json=[{"company_id": LIVE_CO, "name": "Acme"}])
    )
    mock_api.get(f"{FLEET}/sysadmin/companies/{LIVE_CO}/drivers").mock(
        return_value=httpx.Response(200, json=[{"driver_id": "d9", "full_name": "Live Driver"}])
    )
    audit = mock_api.post(f"{FLEET}/sysadmin/impersonation-audit").mock(
        return_value=httpx.Response(201, json={"status": "ok"})
    )

    def cb(data):
        return {"chat_id": 63, "sender_id": 63, "is_callback": True, "callback_data": data}

    await dispatch(cb("sa_live"), bot, fleet)
    await dispatch(cb(f"sa_co_{LIVE_CO}"), bot, fleet)
    await dispatch(cb("sa_role_driver"), bot, fleet)
    await dispatch(cb("sa_drv_d9"), bot, fleet)

    imp = store[63]["impersonation"]
    assert imp["mode"] == "live"
    assert imp == {
        "mode": "live",
        "role": "driver",
        "company_id": LIVE_CO,
        "company_name": "Acme",
        "driver_id": "d9",
        "driver_name": "Live Driver",
        "effective_id": "d9",
        "operator_id": OPERATOR_ID,
        "attendance_enabled": True,
    }
    assert audit.called
    # Audit POSTs use the system-admin caller (operator id, no company scope).
    assert caller_ctx(audit) == {"role": "admin", "impersonator": OPERATOR_ID}
    body = last_body(audit)
    assert body["action"] == "start"
    assert body["effective_role"] == "driver"
    assert body["company_id"] == LIVE_CO
    assert body["effective_id"] == "d9"


async def test_exit_posts_stop_audit_and_clears(store, bot, fleet, mock_api):
    store[64] = {"impersonation": live_imp(role="admin")}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    audit = mock_api.post(f"{FLEET}/sysadmin/impersonation-audit").mock(
        return_value=httpx.Response(201, json={"status": "ok"})
    )
    await dispatch(
        {"chat_id": 64, "sender_id": 64, "is_callback": True, "callback_data": "sa_exit"},
        bot,
        fleet,
    )
    assert audit.called
    assert last_body(audit)["action"] == "stop"
    assert caller_ctx(audit) == {"role": "admin", "impersonator": OPERATOR_ID}
    assert 64 not in store  # impersonation fully cleared
    assert texts.SA_EXITED in sent_texts(bot)
    # A reply keyboard the persona left up (e.g. accident share-location) is removed
    # so the system-admin menu doesn't sit on top of a stale bottom keyboard.
    assert keyboard_removed(bot)


async def test_impersonated_driver_call_carries_impersonator(store, bot, fleet, mock_api):
    store[65] = {"impersonation": live_imp(role="driver", driver_id="d9", effective_id="d9")}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    route = mock_api.post(f"{FLEET}/attendance/clock-in").mock(
        return_value=httpx.Response(200, json={"result": "ok", "time": "08:00"})
    )
    await dispatch(
        {"chat_id": 65, "sender_id": 65, "is_callback": True, "callback_data": "clock_in"},
        bot,
        fleet,
    )
    assert caller_ctx(route) == {
        "role": "admin",
        "company_id": LIVE_CO,
        "impersonator": OPERATOR_ID,
    }


async def test_live_destructive_broadcast_audits_write(store, bot, fleet, mock_api):
    store[66] = {
        "flow": "broadcast",
        "step": "awaiting_confirm",
        "message": "hi",
        "recipients": [111],
        "impersonation": live_imp(role="admin"),
    }
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    audit = mock_api.post(f"{FLEET}/sysadmin/impersonation-audit").mock(
        return_value=httpx.Response(201, json={"status": "ok"})
    )
    await dispatch(
        {"chat_id": 66, "sender_id": 66, "is_callback": True, "callback_data": "broadcast_confirm"},
        bot,
        fleet,
    )
    assert audit.called
    assert last_body(audit)["action"] == "write"
    assert last_body(audit)["detail"] == "broadcast"
    assert texts.BROADCAST_SENT in sent_texts(bot)


async def test_live_non_destructive_does_not_audit(store, bot, fleet, mock_api):
    store[67] = {"impersonation": live_imp(role="admin")}
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    mock_api.get(f"{FLEET}/kpi/daily").mock(return_value=httpx.Response(200, json=[]))
    audit = mock_api.post(f"{FLEET}/sysadmin/impersonation-audit").mock(
        return_value=httpx.Response(201, json={"status": "ok"})
    )
    await dispatch(
        {"chat_id": 67, "sender_id": 67, "is_callback": True, "callback_data": "admin_summary"},
        bot,
        fleet,
    )
    assert not audit.called
