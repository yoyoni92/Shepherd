"""Flow 4.3 - Accident report wizard.

Steps: safe -> location (driver shares it via Telegram) -> description (voice via
Whisper, or text) -> road clear -> 3 document photos -> area video(s) loop ->
POST /accidents -> manager call -> notify admins.
All media is stored as attachments (Fleet API -> Drive); none is run through an LLM
(only the voice description is transcribed).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app import keyboards, sessions, storage, stt, texts
from app.context import Ctx
from app.tg import download, send

_IL = ZoneInfo("Asia/Jerusalem")


async def _store_photo(ctx: Ctx, category: str) -> None:
    data = await download(ctx, ctx.photo_id)
    key = f"accidents/{ctx.chat_id}/{category}.jpg"
    url = await storage.upload(key, data, "image/jpeg", ctx.company_id)
    ctx.state.setdefault("attachments", []).append({"category": category, "file_url": url})


def _fmt_time(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return datetime.now(_IL).strftime("%d/%m/%Y %H:%M")


async def _notify_admins(ctx: Ctx) -> None:
    resp = await ctx.fleet.get("/users", params={"role": "admin"})
    admins = resp.json() if resp.status_code == 200 else []
    msg = texts.ACCIDENT_ADMIN_NOTIFY.format(
        driver=ctx.driver_name or "-", time=_fmt_time(ctx.state.get("datetime"))
    )
    for admin in admins:
        chat = admin.get("telegram_chat_id")
        if chat:
            await ctx.bot.send_message(chat, msg, parse_mode="HTML")


async def accident(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_accident":
        vehicle = await ctx.fleet.driver_vehicle(ctx.driver_id)
        if vehicle is None:
            await send(ctx, texts.NO_VEHICLE)
            return
        await sessions.set_state(
            ctx.chat_id,
            {
                "flow": "accident",
                "step": "awaiting_safe",
                "vehicle_id": vehicle["vehicle_id"],
                "datetime": datetime.now(_IL).isoformat(),
                "attachments": [],
            },
        )
        await send(ctx, texts.ACCIDENT_SAFE_PROMPT, reply_markup=keyboards.accident_safe())
        return

    if route == "accident_safe":
        ctx.state["step"] = "awaiting_location"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.ACCIDENT_LOCATION_PROMPT, reply_markup=keyboards.request_location())
        return

    if route == "accident_location":
        ctx.state["location"] = f"{ctx.location_lat},{ctx.location_lon}"
        ctx.state["step"] = "awaiting_description"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.ACCIDENT_DESCRIPTION_PROMPT)
        return

    if route == "accident_description":
        if ctx.voice_id:
            audio = await download(ctx, ctx.voice_id)
            description = await stt.transcribe(audio)
        else:
            description = ctx.text
        ctx.state["description"] = description
        ctx.state["step"] = "awaiting_road_clear"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(
            ctx, texts.ACCIDENT_ROAD_CLEAR_PROMPT, reply_markup=keyboards.accident_road_clear()
        )
        return

    if route == "accident_road_clear":
        ctx.state["step"] = "awaiting_insurance_photo"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.ACCIDENT_INSURANCE_PROMPT)
        return

    if route == "accident_insurance_photo":
        await _store_photo(ctx, "another_driver_insurance")
        ctx.state["step"] = "awaiting_driver_license_photo"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.ACCIDENT_DRIVER_LICENSE_PROMPT)
        return

    if route == "accident_driver_license":
        await _store_photo(ctx, "another_driver_license")
        ctx.state["step"] = "awaiting_car_license_photo"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.ACCIDENT_CAR_LICENSE_PROMPT)
        return

    if route == "accident_car_license":
        await _store_photo(ctx, "another_car_registration")
        ctx.state["step"] = "awaiting_area_videos"
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(ctx, texts.ACCIDENT_VIDEOS_PROMPT, reply_markup=keyboards.accident_videos_done())
        return

    if route == "accident_area_video":
        idx = ctx.state.get("video_count", 0)
        data = await download(ctx, ctx.video_id)
        key = f"accidents/{ctx.chat_id}/accident_video_{idx}.mp4"
        url = await storage.upload(key, data, "video/mp4", ctx.company_id)
        ctx.state.setdefault("attachments", []).append(
            {"category": "accident_video", "file_url": url}
        )
        ctx.state["video_count"] = idx + 1
        await sessions.set_state(ctx.chat_id, ctx.state)
        await send(
            ctx, texts.ACCIDENT_VIDEO_RECEIVED, reply_markup=keyboards.accident_videos_done()
        )
        return

    if route == "accident_videos_done":
        await ctx.fleet.post(
            "/accidents",
            {
                "vehicle_id": ctx.state["vehicle_id"],
                "driver_id": ctx.driver_id,
                "datetime": ctx.state["datetime"],
                "location": ctx.state.get("location"),
                "description": ctx.state.get("description"),
                "attachments": ctx.state.get("attachments", []),
            },
        )
        await sessions.set_state(
            ctx.chat_id,
            {
                "flow": "accident",
                "step": "awaiting_manager_call",
                "datetime": ctx.state.get("datetime"),
            },
        )
        await send(ctx, texts.ACCIDENT_MANAGER_PROMPT, reply_markup=keyboards.accident_manager())
        return

    if route == "accident_complete":
        await _notify_admins(ctx)
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.ACCIDENT_COMPLETE)
        return
