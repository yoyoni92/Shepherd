"""aiogram long-polling entrypoint. Normalizes every update and hands it to the router."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Message

from app import sessions
from app.config import settings
from app.fleet import FleetClient
from app.router import dispatch

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
_fleet = FleetClient()


def normalize_message(m: Message) -> dict:
    raw: dict = {
        "chat_id": m.chat.id,
        "sender_id": m.from_user.id if m.from_user else None,
        "text": m.text,
    }
    if m.text and m.text.startswith("/"):
        parts = m.text.split(maxsplit=1)
        cmd = parts[0][1:].split("@")[0].lower()  # strip a /command@BotName suffix
        if cmd == "start":
            raw["is_start"] = True
            raw["start_token"] = parts[1].strip() if len(parts) > 1 else None
        else:
            raw["command"] = cmd
        raw["text"] = None
    if m.voice:
        raw["voice_id"] = m.voice.file_id
    if m.photo:
        raw["photo_id"] = m.photo[-1].file_id  # largest size
    if m.video:
        raw["video_id"] = m.video.file_id
    if m.document:
        raw["document_id"] = m.document.file_id
        raw["document_name"] = m.document.file_name
    if m.contact:
        raw["contact_phone"] = m.contact.phone_number
        raw["contact_user_id"] = m.contact.user_id
    if m.location:
        raw["location_lat"] = m.location.latitude
        raw["location_lon"] = m.location.longitude
    return raw


def normalize_callback(c: CallbackQuery) -> dict:
    return {
        "chat_id": c.message.chat.id,
        "sender_id": c.from_user.id if c.from_user else None,
        "is_callback": True,
        "callback_data": c.data,
    }


@dp.message()
async def on_message(message: Message, bot: Bot) -> None:
    await dispatch(normalize_message(message), bot, _fleet)


@dp.callback_query()
async def on_callback(callback: CallbackQuery, bot: Bot) -> None:
    await dispatch(normalize_callback(callback), bot, _fleet)
    await callback.answer()


async def _main() -> None:
    await sessions.open_pool()
    bot = Bot(settings.telegram_bot_token)
    try:
        await dp.start_polling(bot)
    finally:
        await sessions.close_pool()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
