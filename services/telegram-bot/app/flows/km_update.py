"""Flow - Update KM. Driver: own assigned vehicle. Admin: any fleet vehicle.

The reading is tagged source="telegram". Fleet API is the source of truth for the
floor/cap checks; the bot pre-checks the floor for instant feedback and maps the
API's 422 detail to a Hebrew message.
"""

from __future__ import annotations

from app import keyboards, sessions, texts
from app.context import Ctx
from app.tg import send, send_dice


def _prompt(current_km: int | None) -> str:
    return texts.KM_UPDATE_PROMPT.format(current="-" if current_km is None else current_km)


async def _ask_km(ctx: Ctx, vehicle_id: str, current_km: int | None) -> None:
    await sessions.set_state(
        ctx.chat_id,
        {"flow": "km_update", "step": "awaiting_km",
         "vehicle_id": vehicle_id, "current_km": current_km},
    )
    await send(ctx, _prompt(current_km))


async def km_update(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_km_update":
        if ctx.role == "admin":
            resp = await ctx.fleet.get("/vehicles")
            vehicles = resp.json() if resp.status_code == 200 else []
            items = [(v.get("nickname") or v["licensing_plate"], v["vehicle_id"]) for v in vehicles]
            kms = {v["vehicle_id"]: v.get("current_km") for v in vehicles}
            await sessions.set_state(
                ctx.chat_id, {"flow": "km_update", "step": "awaiting_vehicle", "kms": kms}
            )
            await send(
                ctx, texts.KM_PICK_VEHICLE,
                reply_markup=keyboards.pick_list(items, "km_veh_"),
            )
            return
        vehicle = await ctx.fleet.driver_vehicle(ctx.driver_id)
        if vehicle is None:
            await send(ctx, texts.NO_VEHICLE)
            return
        await _ask_km(ctx, vehicle["vehicle_id"], vehicle.get("current_km"))
        return

    if route == "km_update_vehicle":
        vehicle_id = ctx.callback_data.removeprefix("km_veh_")
        current_km = (ctx.state.get("kms") or {}).get(vehicle_id)
        await _ask_km(ctx, vehicle_id, current_km)
        return

    if route == "km_update_value":
        raw = (ctx.text or "").strip().replace(",", "")
        if not raw.isdigit():
            await send(ctx, texts.KM_UPDATE_INVALID)
            return
        km = int(raw)
        current = ctx.state.get("current_km")
        if current is not None and km < current:
            await send(ctx, texts.KM_BELOW_CURRENT)
            return
        resp = await ctx.fleet.post(
            "/km", {"vehicle_id": ctx.state["vehicle_id"], "km": km, "source": "telegram"}
        )
        if resp.status_code == 422:
            detail = resp.json().get("detail")  # Fleet API 422s are always JSON
            msg = texts.KM_BELOW_CURRENT if detail == "km_below_current" else texts.KM_TOO_HIGH
            await send(ctx, msg)
            return
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.KM_UPDATE_DONE)
        await send_dice(ctx)
