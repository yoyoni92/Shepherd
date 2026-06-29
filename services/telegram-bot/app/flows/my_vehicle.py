"""Flow 4.6 - My Vehicle (single-shot card)."""

from __future__ import annotations

from app import fmt, texts
from app.context import Ctx
from app.tg import send


async def my_vehicle(ctx: Ctx, route: str | None) -> None:
    vehicle = await ctx.fleet.driver_vehicle(ctx.driver_id)
    if vehicle is None:
        await send(ctx, texts.NO_VEHICLE)
        return
    km = vehicle.get("current_km")
    km = "-" if km is None else km
    lines = [
        texts.MY_VEHICLE_TITLE,
        fmt.kv("יצרן", vehicle.get("vendor") or "-"),
        fmt.kv("דגם", vehicle.get("model") or "-"),
        fmt.kv("לוחית", vehicle.get("licensing_plate") or "-"),
        fmt.kv("סוג", vehicle.get("vehicle_type") or "-"),
        fmt.kv('ק"מ נוכחי', km),
    ]
    await send(ctx, "\n".join(lines))
