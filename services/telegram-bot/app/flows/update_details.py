"""Flow 4.4 - Update my details (driver self-service)."""

from __future__ import annotations

from app import keyboards, sessions, texts, validate
from app.context import Ctx
from app.tg import send, send_dice

_INVALID = {
    "license_valid": texts.UPDATE_INVALID_DATE,
    "phone": texts.UPDATE_INVALID_PHONE,
    "license_number": texts.UPDATE_INVALID_LICENSE,
}


async def update_details(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_update_details":
        await sessions.set_state(ctx.chat_id, {"flow": "update_details", "step": "awaiting_field"})
        await send(ctx, texts.UPDATE_FIELD_MENU, reply_markup=keyboards.update_details_fields())
        return

    if route == "update_details_field":
        field = validate.field_from_callback(ctx.callback_data)
        await sessions.set_state(
            ctx.chat_id, {"flow": "update_details", "step": "awaiting_value", "field": field}
        )
        await send(ctx, validate.value_prompt(field))
        return

    if route == "update_details_value":
        field_key: str | None = ctx.state.get("field")
        ok, column, value = validate.validate(field_key, ctx.text)
        if not ok:
            await send(ctx, _INVALID.get(field_key or "", texts.UPDATE_INVALID_LICENSE))
            return
        await ctx.fleet.patch(f"/drivers/{ctx.driver_id}", {column: value})
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.UPDATE_DETAILS_DONE)
        await send_dice(ctx)
