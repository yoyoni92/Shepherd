"""Routing core - ports the n8n Route Decision + Active Flow Router.

Every update: resolve whoami + load bot_sessions, then compute `(feature, route)`:
unknown -> invite-claim / access-denied; an active session resumes its flow; a menu
callback starts a feature; otherwise show the role menu.
"""

from __future__ import annotations

from app import sessions
from app.context import Ctx
from app.fleet import FleetClient
from app.flows import FEATURES

# Menu/entry callbacks -> (feature, route). Mirrors the n8n callback lookup.
CALLBACK_MAP: dict[str, tuple[str, str]] = {
    "clock_in": ("clock", "cmd_clock_in"),
    "clock_out": ("clock", "cmd_clock_out"),
    "vehicle_issue": ("vehicle_issue", "cmd_vehicle_issue"),
    "accident_start": ("accident", "cmd_accident"),
    "update_details": ("update_details", "cmd_update_details"),
    "attendance_csv": ("attendance_csv", "cmd_attendance_csv"),
    "my_vehicle": ("my_vehicle", "cmd_my_vehicle"),
    "admin_attendance": ("attendance_admin", "cmd_admin_attendance"),
    "admin_broadcast": ("broadcast", "cmd_admin_broadcast"),
    "admin_summary": ("fleet_summary", "cmd_admin_summary"),
    "admin_update_driver": ("update_driver", "cmd_admin_update_driver"),
    "admin_maintenance": ("maintenance", "cmd_admin_maintenance"),
    "doc_scan": ("doc_scan", "cmd_doc_scan"),
    "maint_overdue": ("maintenance", "cmd_maint_overdue"),
    "maint_log": ("maintenance", "cmd_maint_log"),
    # System admin (Feature 6)
    "sa_overview": ("sysadmin", "overview"),
    "sa_debug": ("sysadmin", "debug_menu"),
    "sa_dbg_driver": ("sysadmin", "debug_driver"),
    "sa_dbg_admin": ("sysadmin", "debug_admin"),
    "sa_live": ("sysadmin", "live_start"),
    "sa_exit": ("sysadmin", "exit"),
    "exit": ("sysadmin", "exit"),
}

FLOW_TO_FEATURE: dict[str, str] = {
    "accident": "accident",
    "vehicle_issue": "vehicle_issue",
    "update_details": "update_details",
    "broadcast": "broadcast",
    "update_driver": "update_driver",
    "maint_log": "maintenance",
    "doc_scan": "doc_scan",
    "sa_live": "sysadmin",
}

# Features requiring a specific role (the Fleet API enforces too; this gates the bot UX).
FEATURE_ROLES: dict[str, str] = {
    "clock": "driver",
    "vehicle_issue": "driver",
    "accident": "driver",
    "update_details": "driver",
    "attendance_csv": "driver",
    "my_vehicle": "driver",
    "attendance_admin": "admin",
    "broadcast": "admin",
    "fleet_summary": "admin",
    "update_driver": "admin",
    "maintenance": "admin",
    "doc_scan": "admin",
}


def active_route(ctx: Ctx) -> str | None:
    """Resume route within the active flow; None when the input doesn't fit the step."""
    flow, step = ctx.flow, ctx.step
    cb = ctx.callback_data if ctx.is_callback else None
    text = ctx.text if not ctx.is_callback else None

    if flow == "accident":
        if step == "awaiting_safe" and cb == "accident_safe":
            return "accident_safe"
        if step == "awaiting_location" and ctx.location_lat is not None:
            return "accident_location"
        if step == "awaiting_description" and (ctx.voice_id or text):
            return "accident_description"
        if step == "awaiting_road_clear" and cb == "accident_road_clear":
            return "accident_road_clear"
        if step == "awaiting_insurance_photo" and ctx.photo_id:
            return "accident_insurance_photo"
        if step == "awaiting_driver_license_photo" and ctx.photo_id:
            return "accident_driver_license"
        if step == "awaiting_car_license_photo" and ctx.photo_id:
            return "accident_car_license"
        if step == "awaiting_area_videos" and ctx.video_id:
            return "accident_area_video"
        if step == "awaiting_area_videos" and cb == "accident_videos_done":
            return "accident_videos_done"
        if step == "awaiting_manager_call" and cb == "accident_manager_called":
            return "accident_complete"
        return None

    if flow == "vehicle_issue":
        if step == "awaiting_description" and text:
            return "vehicle_issue_text"
        return None

    if flow == "update_details":
        if step == "awaiting_field" and cb and cb.startswith("ud_"):
            return "update_details_field"
        if step == "awaiting_value" and text:
            return "update_details_value"
        return None

    if flow == "broadcast":
        if step == "awaiting_message" and text:
            return "broadcast_message"
        if step == "awaiting_confirm" and cb == "broadcast_confirm":
            return "broadcast_send"
        if step == "awaiting_confirm" and cb == "broadcast_cancel":
            return "broadcast_cancel"
        return None

    if flow == "update_driver":
        if step == "awaiting_driver" and cb and cb.startswith("ud2_driver_"):
            return "update_driver_pick"
        if step == "awaiting_field" and cb and cb.startswith("ud2_field_"):
            return "update_driver_field"
        if step == "awaiting_value" and text:
            return "update_driver_value"
        if step == "awaiting_license_file" and (ctx.photo_id or ctx.document_id):
            return "update_driver_license_file"
        if step == "awaiting_license_confirm" and cb == "ud2_lic_confirm":
            return "update_driver_license_apply"
        if step == "awaiting_license_confirm" and cb == "ud2_lic_cancel":
            return "update_driver_license_cancel"
        return None

    if flow == "maint_log":
        if step == "awaiting_vehicle" and cb and cb.startswith("ml_veh_"):
            return "maint_log_vehicle"
        if step == "awaiting_type" and cb and cb.startswith("ml_type_"):
            return "maint_log_type"
        if step == "awaiting_km" and text:
            return "maint_log_km"
        return None

    if flow == "sa_live":
        if step == "pick_company" and cb and cb.startswith("sa_co_"):
            return "live_pick_company"
        if step == "pick_role" and cb in ("sa_role_admin", "sa_role_driver"):
            return "live_pick_role"
        if step == "pick_driver" and cb and cb.startswith("sa_drv_"):
            return "live_pick_driver"
        if step == "pick_admin" and cb and cb.startswith("sa_adm_"):
            return "live_pick_admin"
        return None

    if flow == "doc_scan":
        if step == "awaiting_type" and cb and cb.startswith("ds_type_"):
            return "doc_scan_type"
        if step == "awaiting_driver" and cb and cb.startswith("ds_drv_"):
            return "doc_scan_pick_driver"
        if step == "awaiting_file" and (ctx.photo_id or ctx.document_id):
            return "doc_scan_file"
        if step == "awaiting_confirm" and cb == "ds_confirm":
            return "doc_scan_confirm"
        if step == "awaiting_confirm" and cb == "ds_cancel":
            return "doc_scan_cancel"
        return None

    return None


def route_decision(ctx: Ctx) -> tuple[str, str | None]:
    if ctx.whoami is None:
        # No invites: any unknown user is asked to share their phone, then enrolled
        # by matching it to an active driver / authorization.
        if ctx.contact_phone and ctx.contact_user_id == ctx.sender_id:
            return ("enroll", "enroll_with_phone")
        return ("enroll", "request_phone")

    # A slash command (the ☰ menu) behaves like a menu button: it can start a feature
    # or reopen the menu, taking precedence over an in-progress flow's text step.
    if ctx.command:
        if ctx.command in CALLBACK_MAP:
            return CALLBACK_MAP[ctx.command]
        return ("menu", None)

    ar = active_route(ctx)
    if ar is not None:
        return (FLOW_TO_FEATURE[ctx.flow], ar)

    if ctx.is_callback and ctx.callback_data in CALLBACK_MAP:
        return CALLBACK_MAP[ctx.callback_data]

    return ("menu", None)


async def dispatch(raw: dict, bot, fleet: FleetClient) -> None:
    chat_id = raw["chat_id"]
    whoami = await fleet.whoami(chat_id)
    state = await sessions.get_state(chat_id)
    # System-admin impersonation (Feature 6): when a session carries an impersonation
    # context, rewrite whoami to the effective persona so every existing menu/feature/
    # flow/role path runs as that persona unchanged, and bind the per-update client to
    # the effective company + operator id so Customer-Live writes are auditable.
    imp = state.get("impersonation") if whoami else None
    if imp:
        whoami = {
            "role": imp["role"],
            "driver_id": imp.get("driver_id"),
            "driver_name": imp.get("driver_name"),
            "company_id": imp.get("company_id"),
            "attendance_enabled": imp.get("attendance_enabled", True),
        }
        scoped = fleet.for_company(imp.get("company_id")).as_impersonator(
            imp.get("operator_id")
        )
    elif whoami:
        # Bind the per-update client to the acting user's company so every downstream
        # flow call is tenant-scoped automatically (whoami/enroll stay company-less).
        scoped = fleet.for_company(whoami.get("company_id"))
    else:
        scoped = fleet
    ctx = Ctx(
        chat_id=chat_id,
        bot=bot,
        fleet=scoped,
        whoami=whoami,
        state=state,
        is_callback=raw.get("is_callback", False),
        callback_data=raw.get("callback_data"),
        command=raw.get("command"),
        text=raw.get("text"),
        voice_id=raw.get("voice_id"),
        photo_id=raw.get("photo_id"),
        video_id=raw.get("video_id"),
        document_id=raw.get("document_id"),
        document_name=raw.get("document_name"),
        contact_phone=raw.get("contact_phone"),
        contact_user_id=raw.get("contact_user_id"),
        location_lat=raw.get("location_lat"),
        location_lon=raw.get("location_lon"),
        sender_id=raw.get("sender_id"),
        is_start=raw.get("is_start", False),
        start_token=raw.get("start_token"),
    )

    feature, route = route_decision(ctx)
    required = FEATURE_ROLES.get(feature)
    if required and ctx.role != required:
        feature, route = "access_denied", None

    await FEATURES[feature](ctx, route)
