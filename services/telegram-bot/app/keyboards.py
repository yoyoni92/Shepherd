"""Inline/reply keyboard builders. Callback strings match the n8n workflow 1:1."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app import texts


def _inline(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=data) for label, data in row]
            for row in rows
        ]
    )


def driver_menu(attendance_enabled: bool = True) -> InlineKeyboardMarkup:
    # The clock-in/out row is shown only when the company's attendance flag is on.
    rows: list[list[tuple[str, str]]] = []
    if attendance_enabled:
        rows.append([("⏱ כניסה לעבודה", "clock_in"), ("🚪 יציאה מעבודה", "clock_out")])
    rows += [
        [("🔧 דיווח תקלה", "vehicle_issue")],
        [("🚨 דיווח תאונה", "accident_start")],
        [("✏️ עדכון פרטים", "update_details")],
        [("📊 דוח נוכחות", "attendance_csv"), ("🚗 הרכב שלי", "my_vehicle")],
    ]
    return _inline(rows)


def admin_menu() -> InlineKeyboardMarkup:
    return _inline(
        [
            [("👥 נוכחות היום", "admin_attendance")],
            [("📢 שידור הודעה", "admin_broadcast")],
            [("🚗 סיכום צי", "admin_summary")],
            [("✏️ עדכון נהג", "admin_update_driver")],
            [("🔧 תחזוקה", "admin_maintenance")],
            [("📄 סריקת מסמך", "doc_scan")],
        ]
    )


def sysadmin_menu() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.SA_OVERVIEW_BTN, "sa_overview")],
            [(texts.SA_DEBUG_BTN, "sa_debug")],
            [(texts.SA_LIVE_BTN, "sa_live")],
        ]
    )


def sa_debug_pick() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.SA_DEBUG_DRIVER_BTN, "sa_dbg_driver")],
            [(texts.SA_DEBUG_ADMIN_BTN, "sa_dbg_admin")],
        ]
    )


def sa_live_role_pick() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.SA_ROLE_ADMIN_BTN, "sa_role_admin")],
            [(texts.SA_ROLE_DRIVER_BTN, "sa_role_driver")],
        ]
    )


def sa_exit() -> InlineKeyboardMarkup:
    return _inline([[(texts.SA_EXIT_BTN, "sa_exit")]])


def with_exit(kb: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Append the always-available 'exit impersonation' row to a persona menu."""
    kb.inline_keyboard.append(
        [InlineKeyboardButton(text=texts.SA_EXIT_BTN, callback_data="sa_exit")]
    )
    return kb


def request_contact() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.CLAIM_SHARE_BUTTON, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def request_location() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.ACCIDENT_LOCATION_BUTTON, request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def accident_safe() -> InlineKeyboardMarkup:
    return _inline([[(texts.ACCIDENT_SAFE_BUTTON, "accident_safe")]])


def accident_road_clear() -> InlineKeyboardMarkup:
    return _inline([[(texts.ACCIDENT_ROAD_CLEAR_BUTTON, "accident_road_clear")]])


def accident_videos_done() -> InlineKeyboardMarkup:
    return _inline([[(texts.ACCIDENT_VIDEOS_DONE_BUTTON, "accident_videos_done")]])


def accident_manager() -> InlineKeyboardMarkup:
    return _inline([[(texts.ACCIDENT_MANAGER_BUTTON, "accident_manager_called")]])


def update_details_fields() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.UD_LICENSE_VALID, "ud_license_valid")],
            [(texts.UD_LICENSE_NUMBER, "ud_license_number")],
            [(texts.UD_PHONE, "ud_phone")],
        ]
    )


def update_driver_fields() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.UD_LICENSE_VALID, "ud2_field_license_valid")],
            [(texts.UD_LICENSE_NUMBER, "ud2_field_license_number")],
            [(texts.UD_PHONE, "ud2_field_phone")],
            [(texts.UPDATE_DRIVER_SCAN_BTN, "ud2_field_license_scan")],
        ]
    )


def update_driver_license_confirm() -> InlineKeyboardMarkup:
    return _inline(
        [
            [
                (texts.DOC_SCAN_CONFIRM_BTN, "ud2_lic_confirm"),
                (texts.DOC_SCAN_CANCEL_BTN, "ud2_lic_cancel"),
            ]
        ]
    )


def broadcast_confirm() -> InlineKeyboardMarkup:
    return _inline(
        [
            [
                (texts.BROADCAST_SEND, "broadcast_confirm"),
                (texts.BROADCAST_CANCEL, "broadcast_cancel"),
            ]
        ]
    )


def maintenance_menu() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.MAINT_OVERDUE_BTN, "maint_overdue")],
            [(texts.MAINT_LOG_BTN, "maint_log")],
        ]
    )


def doc_scan_types() -> InlineKeyboardMarkup:
    return _inline(
        [
            [(texts.DOC_TYPE_VEHICLE_LICENSE, "ds_type_vehicle_license")],
            [(texts.DOC_TYPE_INSURANCE, "ds_type_insurance")],
            [(texts.DOC_TYPE_DRIVER_LICENSE, "ds_type_driver_license")],
        ]
    )


def doc_scan_confirm() -> InlineKeyboardMarkup:
    return _inline(
        [[(texts.DOC_SCAN_CONFIRM_BTN, "ds_confirm"), (texts.DOC_SCAN_CANCEL_BTN, "ds_cancel")]]
    )


def pick_list(
    items: list[tuple[str, str]], prefix: str, cap: int = 50, icon: str = ""
) -> InlineKeyboardMarkup:
    """One button per row: (label, id) -> callback `{prefix}{id}`. Capped, no pagination."""
    pre = f"{icon} " if icon else ""
    return _inline([[(f"{pre}{label}", f"{prefix}{value}")] for label, value in items[:cap]])
