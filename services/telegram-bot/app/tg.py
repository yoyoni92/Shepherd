"""Thin Telegram I/O helpers over the aiogram Bot (kept tiny so flows stay readable)."""

from __future__ import annotations

from typing import Any

from aiogram.types import BufferedInputFile

from app.context import Ctx


async def send(ctx: Ctx, text: str, reply_markup: Any | None = None) -> None:
    await ctx.bot.send_message(ctx.chat_id, text, reply_markup=reply_markup, parse_mode="HTML")


async def send_document(ctx: Ctx, filename: str, data: bytes, caption: str | None = None) -> None:
    await ctx.bot.send_document(
        ctx.chat_id, BufferedInputFile(data, filename=filename), caption=caption
    )


async def download(ctx: Ctx, file_id: str) -> bytes:
    """Fetch a Telegram file's bytes (voice/photo/video/document)."""
    f = await ctx.bot.get_file(file_id)
    buf = await ctx.bot.download_file(f.file_path)
    return buf.read()


async def send_dice(ctx: Ctx, emoji: str = "🎯") -> None:
    """Animated-emoji flourish (Bot API sendDice) on a successful completion.
    Only 🎲 🎯 🏀 ⚽ 🎳 🎰 are supported; the value is random and ignored here."""
    await ctx.bot.send_dice(ctx.chat_id, emoji=emoji)
