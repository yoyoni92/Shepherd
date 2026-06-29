"""Telegram command menu (the blue ☰ button) - per-role command lists.

Set per-chat after a user is authorized so a driver sees driver actions and an admin
sees admin actions. Command words match `router.CALLBACK_MAP` keys, so tapping one
routes to the same feature as the equivalent inline button.
"""

from __future__ import annotations

from aiogram.types import BotCommand, BotCommandScopeChat

DRIVER_COMMANDS = [
    ("menu", "תפריט"),
    ("clock_in", "כניסה לעבודה"),
    ("clock_out", "יציאה מעבודה"),
    ("vehicle_issue", "דיווח תקלה"),
    ("accident_start", "דיווח תאונה"),
    ("update_details", "עדכון פרטים"),
    ("km_update", 'עדכון ק"מ'),
    ("attendance_csv", "דוח נוכחות"),
    ("my_vehicle", "הרכב שלי"),
]
ADMIN_COMMANDS = [
    ("menu", "תפריט"),
    ("admin_attendance", "נוכחות היום"),
    ("admin_broadcast", "שידור הודעה"),
    ("admin_summary", "סיכום צי"),
    ("admin_update_driver", "עדכון נהג"),
    ("km_update", 'עדכון ק"מ'),
    ("admin_maintenance", "תחזוקה"),
    ("doc_scan", "סריקת מסמך"),
]
# The platform operator's own cross-company commands. Passed via role="system_admin"
# (a sysadmin's whoami role is "admin", so the caller signals this context explicitly).
SYSADMIN_COMMANDS = [
    ("menu", "תפריט"),
    ("sa_overview", "סקירת מערכת"),
    ("sa_debug", "מצב דיבאג"),
    ("sa_live", "לקוח חי"),
]


async def apply(
    bot, chat_id: int, role: str | None, attendance_enabled: bool = False
) -> None:
    """Set the chat's command menu to the role-appropriate list (idempotent).

    Drivers see clock-in/out only when their company's attendance flag is on.
    """
    if role == "system_admin":
        cmds = SYSADMIN_COMMANDS
    elif role == "admin":
        cmds = ADMIN_COMMANDS
    elif attendance_enabled:
        cmds = DRIVER_COMMANDS
    else:
        cmds = [c for c in DRIVER_COMMANDS if c[0] not in ("clock_in", "clock_out")]
    await bot.set_my_commands(
        [BotCommand(command=c, description=d) for c, d in cmds],
        scope=BotCommandScopeChat(chat_id=chat_id),
    )
