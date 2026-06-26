"""Cross-system integration tests against the live compose stack.

Each test drives the real bot through real Telegram updates and asserts the **real
side effects** in Postgres (rows written via Fleet API) - not just the bot's replies.
Telegram and the LLM/S3 boundaries are the only mocks. One user per role.

Run with the stack up:  make up  &&  make e2e
"""

from __future__ import annotations

from app import texts
from identities import (
    ADMIN_CHAT,
    ADMIN_CONTACT,
    DRIVER_CHAT,
    DRIVER_CONTACT,
    DRIVER_ID,
    MAINTENANCE_TYPE_NAME,
    PLATE,
    UNKNOWN_CHAT,
    UNKNOWN_CONTACT,
    VEHICLE_ID,
)


def q(db, sql, *params):
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall() if cur.description else []


# ============================ Enrollment (real users rows) ============================


async def test_unknown_user_typed_text_nudged_to_button(sim, rec):
    # Typing instead of tapping the share-contact button -> nudge, not enrollment.
    await sim.text(UNKNOWN_CHAT, "0528588058")
    assert texts.CLAIM_USE_BUTTON in rec.sent_texts()


async def test_enroll_driver_writes_bot_user(sim, rec, db):
    await sim.share_contact(DRIVER_CHAT, DRIVER_CONTACT)
    assert texts.WELCOME_DRIVER in rec.sent_texts()
    rows = q(db, "SELECT role, driver_id FROM users WHERE telegram_chat_id = %s", DRIVER_CHAT)
    assert rows == [("driver", DRIVER_ID)]


async def test_enroll_admin_writes_bot_user(sim, rec, db):
    await sim.share_contact(ADMIN_CHAT, ADMIN_CONTACT)
    assert texts.WELCOME_ADMIN in rec.sent_texts()
    rows = q(db, "SELECT role FROM users WHERE telegram_chat_id = %s", ADMIN_CHAT)
    assert rows == [("admin",)]


async def test_enroll_unknown_phone_not_authorized(sim, rec, db):
    await sim.share_contact(UNKNOWN_CHAT, UNKNOWN_CONTACT)
    assert texts.NOT_AUTHORIZED in rec.sent_texts()
    assert q(db, "SELECT 1 FROM users WHERE telegram_chat_id = %s", UNKNOWN_CHAT) == []


# ============================ Driver flows ============================


async def test_clock_in_writes_attendance_row(sim, rec, db, driver_user):
    await sim.tap(DRIVER_CHAT, "clock_in")
    assert any(t.startswith("✅ כניסה נרשמה") for t in rec.sent_texts())
    assert rec.dice_count() == 1
    rows = q(
        db,
        "SELECT clock_in FROM attendance_records "
        "WHERE driver_id = %s AND work_date = current_date",
        DRIVER_ID,
    )
    assert len(rows) == 1 and rows[0][0] is not None


async def test_clock_out_updates_attendance_row(sim, rec, db, driver_user):
    await sim.tap(DRIVER_CHAT, "clock_in")
    await sim.tap(DRIVER_CHAT, "clock_out")
    rows = q(
        db,
        "SELECT clock_out FROM attendance_records "
        "WHERE driver_id = %s AND work_date = current_date",
        DRIVER_ID,
    )
    assert len(rows) == 1 and rows[0][0] is not None


async def test_vehicle_issue_writes_event_row(sim, rec, db, driver_user):
    await sim.tap(DRIVER_CHAT, "vehicle_issue")
    await sim.text(DRIVER_CHAT, "הבלם לא עובד")
    assert texts.VEHICLE_ISSUE_DONE in rec.sent_texts()
    rows = q(
        db,
        "SELECT event_type, source_type, message FROM events "
        "WHERE event_type = 'vehicle_issue' AND message LIKE %s",
        "%הבלם לא עובד%",
    )
    assert len(rows) == 1
    assert rows[0][0] == "vehicle_issue" and rows[0][1] == "telegram"


async def test_accident_persists_accident_and_attachments(sim, rec, db, driver_user, admin_user):
    await sim.tap(DRIVER_CHAT, "accident_start")
    await sim.tap(DRIVER_CHAT, "accident_safe")
    await sim.text(DRIVER_CHAT, "פגעתי בעמוד")
    await sim.tap(DRIVER_CHAT, "accident_road_clear")
    await sim.photo(DRIVER_CHAT)  # other driver's insurance
    await sim.photo(DRIVER_CHAT)  # other driver's license
    await sim.photo(DRIVER_CHAT)  # other car's registration
    await sim.video(DRIVER_CHAT)  # scene video
    await sim.tap(DRIVER_CHAT, "accident_videos_done")  # POST /accidents

    accidents = q(
        db, "SELECT accident_id, description FROM accidents WHERE vehicle_id = %s", VEHICLE_ID
    )
    assert len(accidents) == 1
    accident_id, description = accidents[0]
    assert description == "פגעתי בעמוד"
    attachments = q(
        db, "SELECT count(*) FROM accident_attachments WHERE accident_id = %s", accident_id
    )
    assert attachments[0][0] == 4  # 3 photos + 1 video

    await sim.tap(DRIVER_CHAT, "accident_manager_called")  # notifies admins
    assert rec.sent_to(ADMIN_CHAT)  # the enrolled admin received the alert
    assert texts.ACCIDENT_COMPLETE in rec.sent_texts()
    assert rec.dice_count() == 0  # accident is excluded from the flourish


async def test_update_details_patches_driver(sim, rec, db, driver_user):
    await sim.tap(DRIVER_CHAT, "update_details")
    await sim.tap(DRIVER_CHAT, "ud_phone")
    await sim.text(DRIVER_CHAT, "0501112222")
    assert texts.UPDATE_DETAILS_DONE in rec.sent_texts()
    rows = q(db, "SELECT phone_number FROM drivers WHERE driver_id = %s", DRIVER_ID)
    assert rows[0][0] == "0501112222"


async def test_attendance_csv_built_from_real_rows(sim, rec, driver_user):
    await sim.tap(DRIVER_CHAT, "clock_in")  # create a real attendance row first
    await sim.tap(DRIVER_CHAT, "attendance_csv")
    docs = rec.documents()
    assert len(docs) == 1
    assert docs[0].document.filename.startswith("נוכחות ")  # Hebrew "נוכחות <month> <year>.csv"


async def test_my_vehicle_card_from_real_vehicle(sim, rec, driver_user):
    await sim.tap(DRIVER_CHAT, "my_vehicle")
    card = next(t for t in rec.sent_texts() if texts.MY_VEHICLE_TITLE in t)
    assert PLATE in card and "Toyota" in card


async def test_driver_blocked_from_admin_feature(sim, rec, driver_user):
    await sim.tap(DRIVER_CHAT, "admin_attendance")
    assert rec.sent_texts() == [texts.ACCESS_DENIED]


# ============================ Admin flows ============================


async def test_admin_attendance_today_shows_clocked_in_driver(sim, rec, admin_user, driver_user):
    await sim.tap(DRIVER_CHAT, "clock_in")  # real attendance row
    await sim.tap(ADMIN_CHAT, "admin_attendance")
    report = next(t for t in rec.sent_texts() if texts.ATTENDANCE_TODAY_TITLE in t)
    assert "E2E Driver" in report


async def test_admin_broadcast_delivers_to_drivers(sim, rec, admin_user, driver_user):
    await sim.tap(ADMIN_CHAT, "admin_broadcast")
    await sim.text(ADMIN_CHAT, "הודעה לכל הנהגים")
    await sim.tap(ADMIN_CHAT, "broadcast_confirm")
    assert rec.sent_to(DRIVER_CHAT) == ["הודעה לכל הנהגים"]
    assert texts.BROADCAST_SENT in rec.sent_texts()
    assert rec.dice_count() == 1


async def test_admin_fleet_summary_from_kpi(sim, rec, db, admin_user):
    q(db, "SELECT refresh_kpi_daily()")  # ensure a snapshot exists
    await sim.tap(ADMIN_CHAT, "admin_summary")
    assert any(texts.FLEET_SUMMARY_TITLE in t for t in rec.sent_texts())


async def test_admin_update_driver_patches_phone(sim, rec, db, admin_user):
    await sim.tap(ADMIN_CHAT, "admin_update_driver")
    await sim.tap(ADMIN_CHAT, f"ud2_driver_{DRIVER_ID}")
    await sim.tap(ADMIN_CHAT, "ud2_field_phone")
    await sim.text(ADMIN_CHAT, "0503334444")
    assert texts.UPDATE_DRIVER_DONE in rec.sent_texts()
    rows = q(db, "SELECT phone_number FROM drivers WHERE driver_id = %s", DRIVER_ID)
    assert rows[0][0] == "0503334444"


async def test_admin_update_driver_license_scan_patches(sim, rec, db, admin_user):
    await sim.tap(ADMIN_CHAT, "admin_update_driver")
    await sim.tap(ADMIN_CHAT, f"ud2_driver_{DRIVER_ID}")
    await sim.tap(ADMIN_CHAT, "ud2_field_license_scan")
    await sim.photo(ADMIN_CHAT)  # Gemini stub returns license number + expiry
    assert any("E2E-LIC-77" in t for t in rec.sent_texts())
    await sim.tap(ADMIN_CHAT, "ud2_lic_confirm")
    rows = q(
        db,
        "SELECT license_number, license_valid_to FROM drivers WHERE driver_id = %s",
        DRIVER_ID,
    )
    assert rows[0][0] == "E2E-LIC-77"
    assert str(rows[0][1]) == "2031-03-03"


async def test_admin_maintenance_overdue_lists_vehicle(sim, rec, admin_user):
    await sim.tap(ADMIN_CHAT, "admin_maintenance")
    await sim.tap(ADMIN_CHAT, "maint_overdue")
    overdue = next(t for t in rec.sent_texts() if texts.MAINT_OVERDUE_TITLE in t)
    assert PLATE in overdue


async def test_admin_maintenance_log_writes_care_row(sim, rec, db, admin_user):
    await sim.tap(ADMIN_CHAT, "admin_maintenance")
    await sim.tap(ADMIN_CHAT, "maint_log")
    await sim.tap(ADMIN_CHAT, f"ml_veh_{VEHICLE_ID}")
    await sim.tap(ADMIN_CHAT, f"ml_type_{MAINTENANCE_TYPE_NAME}")
    await sim.text(ADMIN_CHAT, "65000")
    assert texts.MAINT_LOGGED in rec.sent_texts()
    assert rec.dice_count() == 1
    rows = q(
        db,
        "SELECT km_at_service, maintenance_type FROM vehicle_care WHERE vehicle_id = %s",
        VEHICLE_ID,
    )
    assert rows == [(65000, MAINTENANCE_TYPE_NAME)]


async def test_admin_doc_scan_vehicle_license_updates_vehicle(sim, rec, db, admin_user):
    await sim.tap(ADMIN_CHAT, "doc_scan")
    await sim.tap(ADMIN_CHAT, "ds_type_vehicle_license")
    await sim.photo(ADMIN_CHAT)  # Gemini stub returns plate + valid_to
    assert any(PLATE in t for t in rec.sent_texts())  # confirm screen
    await sim.tap(ADMIN_CHAT, "ds_confirm")
    assert texts.DOC_SCAN_APPLIED in rec.sent_texts()
    rows = q(db, "SELECT license_valid_to FROM vehicles WHERE vehicle_id = %s", VEHICLE_ID)
    assert str(rows[0][0]) == "2030-02-02"


async def test_admin_doc_scan_insurance_updates_vehicle(sim, rec, db, admin_user):
    await sim.tap(ADMIN_CHAT, "doc_scan")
    await sim.tap(ADMIN_CHAT, "ds_type_insurance")
    await sim.photo(ADMIN_CHAT)
    await sim.tap(ADMIN_CHAT, "ds_confirm")
    assert texts.DOC_SCAN_APPLIED in rec.sent_texts()
    rows = q(db, "SELECT insurance_valid_to FROM vehicles WHERE vehicle_id = %s", VEHICLE_ID)
    assert str(rows[0][0]) == "2030-02-02"


async def test_admin_doc_scan_driver_license_patches_driver(sim, rec, db, admin_user):
    await sim.tap(ADMIN_CHAT, "doc_scan")
    await sim.tap(ADMIN_CHAT, "ds_type_driver_license")
    await sim.tap(ADMIN_CHAT, f"ds_drv_{DRIVER_ID}")
    await sim.photo(ADMIN_CHAT)
    await sim.tap(ADMIN_CHAT, "ds_confirm")
    assert texts.DOC_SCAN_APPLIED in rec.sent_texts()
    rows = q(db, "SELECT license_number FROM drivers WHERE driver_id = %s", DRIVER_ID)
    assert rows[0][0] == "E2E-LIC-77"
