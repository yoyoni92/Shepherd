"""Flow 5.5 - Maintenance: view overdue (km-based) + log a maintenance event."""

from __future__ import annotations

from datetime import date

from app import keyboards, sessions, texts
from app.context import Ctx
from app.tg import send, send_dice


def _overdue(vehicles: list[dict]) -> list[tuple[dict, int]]:
    out = []
    for v in vehicles:
        cur, nxt = v.get("current_km"), v.get("next_maintenance_km")
        if cur is not None and nxt is not None and cur >= nxt:
            out.append((v, cur - nxt))
    out.sort(key=lambda t: t[1], reverse=True)
    return out


async def maintenance(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_admin_maintenance":
        await send(ctx, texts.MAINT_MENU, reply_markup=keyboards.maintenance_menu())
        return

    if route == "cmd_maint_overdue":
        resp = await ctx.fleet.get("/vehicles")
        vehicles = resp.json() if resp.status_code == 200 else []
        overdue = _overdue(vehicles)
        if not overdue:
            await send(ctx, texts.MAINT_OVERDUE_EMPTY)
            return
        lines = [texts.MAINT_OVERDUE_TITLE, ""]
        for v, over in overdue:
            lines.append(f"• {v.get('licensing_plate')}: באיחור {over} ק\"מ")
        await send(ctx, "\n".join(lines))
        return

    if route == "cmd_maint_log":
        resp = await ctx.fleet.get("/vehicles")
        vehicles = resp.json() if resp.status_code == 200 else []
        items = [(v.get("nickname") or v["licensing_plate"], v["vehicle_id"]) for v in vehicles]
        await sessions.set_state(ctx.chat_id, {"flow": "maint_log", "step": "awaiting_vehicle"})
        await send(
            ctx, texts.MAINT_PICK_VEHICLE, reply_markup=keyboards.pick_list(items, "ml_veh_")
        )
        return

    if route == "maint_log_vehicle":
        vehicle_id = ctx.callback_data.removeprefix("ml_veh_")
        resp = await ctx.fleet.get("/maintenance-types")
        types = resp.json() if resp.status_code == 200 else []
        items = [(t["name"], t["name"]) for t in types]
        await sessions.set_state(
            ctx.chat_id,
            {
                "flow": "maint_log",
                "step": "awaiting_type",
                "vehicle_id": vehicle_id,
            },
        )
        await send(
            ctx, texts.MAINT_PICK_TYPE, reply_markup=keyboards.pick_list(items, "ml_type_", cap=64)
        )
        return

    if route == "maint_log_type":
        ctx.state.update(step="awaiting_km", maint_type=ctx.callback_data.removeprefix("ml_type_"))
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.MAINT_KM_PROMPT)
        return

    if route == "maint_log_km":
        raw = (ctx.text or "").strip().replace(",", "")
        if not raw.isdigit():
            await send(ctx, texts.MAINT_KM_INVALID)
            return
        await ctx.fleet.post(
            "/vehicle_care",
            {
                "vehicle_id": ctx.state["vehicle_id"],
                "service_date": date.today().isoformat(),
                "maintenance_type": ctx.state["maint_type"],
                "km_at_service": int(raw),
            },
        )
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.MAINT_LOGGED)
        await send_dice(ctx)
