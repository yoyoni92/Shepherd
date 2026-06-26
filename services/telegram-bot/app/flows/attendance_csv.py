"""Flow 4.5 - Monthly attendance CSV (current month, driver self)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app import texts
from app.context import Ctx
from app.tg import send, send_document

_IL = ZoneInfo("Asia/Jerusalem")


def _hours(clock_in: str | None, clock_out: str | None) -> str:
    if not clock_in or not clock_out:
        return ""
    try:
        a = datetime.strptime(clock_in, "%H:%M")
        b = datetime.strptime(clock_out, "%H:%M")
    except ValueError:
        return ""
    return f"{(b - a).total_seconds() / 3600:.2f}"


def build_csv(rows: list[dict]) -> bytes:
    lines = ["תאריך,כניסה,יציאה,שעות"]
    for r in rows:
        lines.append(
            f"{r.get('work_date', '')},{r.get('clock_in') or ''},"
            f"{r.get('clock_out') or ''},{_hours(r.get('clock_in'), r.get('clock_out'))}"
        )
    # UTF-8 BOM so Excel renders Hebrew correctly.
    return ("﻿" + "\n".join(lines)).encode("utf-8")


async def attendance_csv(ctx: Ctx, route: str | None) -> None:
    now = datetime.now(_IL)
    month = now.strftime("%Y-%m")
    resp = await ctx.fleet.get(f"/attendance/{month}", params={"driver_id": ctx.driver_id})
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        await send(ctx, texts.ATTENDANCE_EMPTY)
        return
    month_name = texts.HEB_MONTHS[now.month - 1]
    caption = texts.ATTENDANCE_CSV_CAPTION.format(month=month_name)
    filename = texts.ATTENDANCE_CSV_FILENAME.format(month=month_name, year=now.year)
    await send_document(ctx, filename, build_csv(rows), caption=caption)
