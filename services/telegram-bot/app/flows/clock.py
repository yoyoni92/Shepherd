"""Flow 4.1 - Clock in / out. The reporting window is enforced server-side."""

from __future__ import annotations

from app import texts
from app.context import Ctx
from app.tg import send, send_dice


async def clock(ctx: Ctx, route: str | None) -> None:
    # Attendance is opt-in per company; deny instead of hitting the API when it's off.
    if not ctx.attendance_enabled:
        await send(ctx, texts.ATTENDANCE_DISABLED)
        return
    path = "/attendance/clock-in" if route == "cmd_clock_in" else "/attendance/clock-out"
    resp = await ctx.fleet.post(path, {"driver_id": ctx.driver_id})
    data = resp.json()
    result = data.get("result")

    if result == "blocked":
        msg = texts.CLOCK_BLOCKED.format(start=data.get("window_start"), end=data.get("window_end"))
    elif route == "cmd_clock_in":
        msg = {
            "ok": texts.CLOCK_IN_OK.format(time=data.get("time")),
            "already_in": texts.CLOCK_IN_ALREADY,
        }.get(result, texts.CLOCK_IN_ALREADY)
    else:
        msg = {
            "ok": texts.CLOCK_OUT_OK.format(time=data.get("time"), hours=data.get("hours")),
            "no_open": texts.CLOCK_OUT_NO_OPEN,
        }.get(result, texts.CLOCK_OUT_NO_OPEN)

    await send(ctx, msg)
    if result == "ok":
        await send_dice(ctx)
