"""Flow 5.4 - Update driver (admin picks driver -> field -> value).

The field menu also offers "scan driver license": the admin uploads the license, Gemini
vision extracts license number + expiry, and the admin approves before it's applied.
"""

from __future__ import annotations

from app import keyboards, sessions, texts, validate, vision
from app.context import Ctx
from app.tg import download, send, send_dice

_INVALID = {
    "license_valid": texts.UPDATE_INVALID_DATE,
    "phone": texts.UPDATE_INVALID_PHONE,
    "license_number": texts.UPDATE_INVALID_LICENSE,
}


async def update_driver(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_admin_update_driver":
        resp = await ctx.fleet.get("/drivers")
        drivers = resp.json() if resp.status_code == 200 else []
        items = [(d["full_name"], d["driver_id"]) for d in drivers]
        await sessions.set_state(ctx.chat_id, {"flow": "update_driver", "step": "awaiting_driver"})
        await send(
            ctx,
            texts.UPDATE_DRIVER_PICK,
            reply_markup=keyboards.pick_list(items, "ud2_driver_", icon="👤"),
        )
        return

    if route == "update_driver_pick":
        target = ctx.callback_data.removeprefix("ud2_driver_")
        await sessions.set_state(
            ctx.chat_id,
            {"flow": "update_driver", "step": "awaiting_field", "target_driver_id": target},
        )
        await send(ctx, texts.UPDATE_FIELD_MENU, reply_markup=keyboards.update_driver_fields())
        return

    if route == "update_driver_field":
        # Branch to the vision scan instead of a manual field entry.
        if ctx.callback_data == "ud2_field_license_scan":
            ctx.state.update(step="awaiting_license_file")
            await sessions.set_state(ctx.chat_id, ctx.state)
            await send(ctx, texts.UPDATE_DRIVER_SCAN_PROMPT)
            return
        field = validate.field_from_callback(ctx.callback_data)
        ctx.state.update(step="awaiting_value", field=field)
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, validate.value_prompt(field))
        return

    if route == "update_driver_value":
        field = ctx.state.get("field")
        ok, column, value = validate.validate(field, ctx.text)
        if not ok:
            await send(ctx, _INVALID.get(field, texts.UPDATE_INVALID_LICENSE))
            return
        await ctx.fleet.patch(f"/drivers/{ctx.state['target_driver_id']}", {column: value})
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.UPDATE_DRIVER_DONE)
        await send_dice(ctx)
        return

    if route == "update_driver_license_file":
        await send(ctx, texts.DOC_SCAN_ANALYZING)
        data = await download(ctx, ctx.photo_id or ctx.document_id)
        is_pdf = bool(ctx.document_name and ctx.document_name.lower().endswith(".pdf"))
        mime = "application/pdf" if is_pdf else "image/jpeg"
        fields = await vision.extract("driver_license", data, mime)
        if not fields or not (fields.get("license_number") or fields.get("valid_to")):
            await send(ctx, texts.DOC_SCAN_FAILED)  # stay on awaiting_license_file to retry
            return
        ctx.state.update(step="awaiting_license_confirm", lic_fields=fields)
        await sessions.set_state(ctx.chat_id, ctx.state)
        details = (
            f"{texts.DOC_SCAN_CONFIRM_TITLE}\n\n"
            f"מספר רישיון: {fields.get('license_number') or '-'}\n"
            f"בתוקף עד: {fields.get('valid_to') or '-'}"
        )
        await send(ctx, details, reply_markup=keyboards.update_driver_license_confirm())
        return

    if route == "update_driver_license_apply":
        fields = ctx.state.get("lic_fields", {})
        body = {}
        if fields.get("license_number"):
            body["license_number"] = fields["license_number"]
        if fields.get("valid_to"):
            body["license_valid_to"] = fields["valid_to"]
        await ctx.fleet.patch(f"/drivers/{ctx.state['target_driver_id']}", body)
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.UPDATE_DRIVER_DONE)
        await send_dice(ctx)
        return

    if route == "update_driver_license_cancel":
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.DOC_SCAN_CANCELLED)
        return
