"""Admin document scan (Point 2): choose type -> upload -> Gemini vision ->
confirm -> apply via Fleet API. Guided, not free upload.

Vehicle docs (license / insurance) apply through POST /documents/extracted
(plate-matched upsert). Driver license applies through PATCH /drivers/{id}.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app import keyboards, sessions, storage, texts, vision
from app.context import Ctx
from app.tg import download, send, send_dice

# callback -> internal vision doc_type
_TYPE = {
    "ds_type_vehicle_license": "vehicle_license",
    "ds_type_insurance": "insurance",
    "ds_type_driver_license": "driver_license",
}


def _confirm_text(doc_type: str, fields: dict) -> str:
    lines = [texts.DOC_SCAN_CONFIRM_TITLE, ""]
    if doc_type == "driver_license":
        lines.append(f"מספר רישיון: {fields.get('license_number') or '-'}")
    else:
        lines.append(f"לוחית: {fields.get('plate_number') or '-'}")
    lines.append(f"בתוקף עד: {fields.get('valid_to') or '-'}")
    return "\n".join(lines)


async def _apply(ctx: Ctx) -> str:
    doc_type = ctx.state["doc_type"]
    fields = ctx.state.get("fields", {})
    file_url = ctx.state.get("file_url")

    if doc_type == "driver_license":
        body = {}
        if fields.get("license_number"):
            body["license_number"] = fields["license_number"]
        if fields.get("valid_to"):
            body["license_valid_to"] = fields["valid_to"]
        await ctx.fleet.patch(f"/drivers/{ctx.state['target_driver_id']}", body)
        return texts.DOC_SCAN_APPLIED

    plate = fields.get("plate_number")
    if not plate:
        return texts.DOC_SCAN_REVIEW
    if doc_type == "insurance":
        payload = {
            "doc_type": "insurance",
            "licensing_plate": plate,
            "insurance_valid_to": fields.get("valid_to"),
            "insurance_file_url": file_url,
        }
    else:  # vehicle_license
        payload = {
            "doc_type": "license",
            "licensing_plate": plate,
            "license_valid_to": fields.get("valid_to"),
            "license_file_url": file_url,
        }
    resp = await ctx.fleet.post("/documents/extracted", payload)
    status = resp.json().get("status") if resp.status_code == 200 else None
    return texts.DOC_SCAN_APPLIED if status == "updated" else texts.DOC_SCAN_REVIEW


async def doc_scan(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_doc_scan":
        await sessions.set_state(ctx.chat_id, {"flow": "doc_scan", "step": "awaiting_type"})
        await send(ctx, texts.DOC_SCAN_PICK_TYPE, reply_markup=keyboards.doc_scan_types())
        return

    if route == "doc_scan_type":
        assert ctx.callback_data is not None
        doc_type = _TYPE.get(ctx.callback_data)
        if doc_type == "driver_license":
            resp = await ctx.fleet.get("/drivers")
            drivers = resp.json() if resp.status_code == 200 else []
            items = [(d["full_name"], d["driver_id"]) for d in drivers]
            await sessions.set_state(
                ctx.chat_id,
                {
                    "flow": "doc_scan",
                    "step": "awaiting_driver",
                    "doc_type": doc_type,
                },
            )
            await send(
                ctx, texts.DOC_SCAN_PICK_DRIVER, reply_markup=keyboards.pick_list(items, "ds_drv_")
            )
            return
        await sessions.set_state(
            ctx.chat_id,
            {
                "flow": "doc_scan",
                "step": "awaiting_file",
                "doc_type": doc_type,
            },
        )
        await send(ctx, texts.DOC_SCAN_SEND_FILE)
        return

    if route == "doc_scan_pick_driver":
        assert ctx.callback_data is not None
        ctx.state.update(
            step="awaiting_file", target_driver_id=ctx.callback_data.removeprefix("ds_drv_")
        )
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.DOC_SCAN_SEND_FILE)
        return

    if route == "doc_scan_file":
        await send(ctx, texts.DOC_SCAN_ANALYZING)
        file_id = ctx.photo_id or ctx.document_id
        assert file_id is not None, "photo_id or document_id must be set for doc_scan_file route"
        data = await download(ctx, file_id)
        is_pdf = bool(ctx.document_name and ctx.document_name.lower().endswith(".pdf"))
        mime = "application/pdf" if is_pdf else "image/jpeg"
        ext = "pdf" if is_pdf else "jpg"
        doc_type = ctx.state["doc_type"]
        key = f"documents/{doc_type}/{ctx.chat_id}_{datetime.now(UTC):%Y%m%d%H%M%S}.{ext}"
        url = await storage.upload(key, data, mime, ctx.company_id)
        fields = await vision.extract(doc_type, data, mime)
        if not fields:
            await send(ctx, texts.DOC_SCAN_FAILED)  # stay on awaiting_file to retry
            return
        ctx.state.update(step="awaiting_confirm", file_url=url, fields=fields)
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, _confirm_text(doc_type, fields), reply_markup=keyboards.doc_scan_confirm())
        return

    if route == "doc_scan_confirm":
        result = await _apply(ctx)
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, result)
        if result == texts.DOC_SCAN_APPLIED:
            await send_dice(ctx)
        return

    if route == "doc_scan_cancel":
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.DOC_SCAN_CANCELLED)
        return
