"""Flow 4.2 - Report vehicle issue (free text -> events)."""

from __future__ import annotations

from app import sessions, texts
from app.context import Ctx
from app.tg import send, send_dice


async def vehicle_issue(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_vehicle_issue":
        await sessions.set_state(
            ctx.chat_id, {"flow": "vehicle_issue", "step": "awaiting_description"}
        )
        await send(ctx, texts.VEHICLE_ISSUE_PROMPT)
        return

    if route == "vehicle_issue_text":
        vehicle = await ctx.fleet.driver_vehicle(ctx.driver_id)
        await sessions.clear_state(ctx.chat_id)
        if vehicle is None:
            await send(ctx, texts.NO_VEHICLE)
            return
        await ctx.fleet.post(
            "/events",
            {
                "vehicle_id": vehicle["vehicle_id"],
                "event_type": "warning",
                "severity": "warning",
                "message": f"תקלה מהנהג: {ctx.text}",
                "source_type": "telegram",
            },
        )
        await send(ctx, texts.VEHICLE_ISSUE_DONE)
        await send_dice(ctx)
