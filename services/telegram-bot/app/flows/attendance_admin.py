"""Flow 5.1 - Today's attendance (admin, single-shot)."""

from __future__ import annotations

from app import fmt, texts
from app.context import Ctx
from app.tg import send

_STATUS_HE = {"present": "נוכח", "late": "איחור", "leave": "חופשה", "absent": "נעדר"}


async def attendance_admin(ctx: Ctx, route: str | None) -> None:
    resp = await ctx.fleet.get("/attendance/today")
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        await send(ctx, texts.ATTENDANCE_EMPTY)
        return
    lines = [texts.ATTENDANCE_TODAY_TITLE, ""]
    for r in rows:
        name = r.get("driver_name") or str(r.get("driver_id"))
        clock_in = r.get("clock_in") or "-"
        clock_out = r.get("clock_out") or "-"
        status = _STATUS_HE.get(r.get("status"), r.get("status") or "")
        lines.append(
            f"• {name}: {fmt.val(clock_in)} - {fmt.val(clock_out)} ({status})"
        )
    await send(ctx, "\n".join(lines))
