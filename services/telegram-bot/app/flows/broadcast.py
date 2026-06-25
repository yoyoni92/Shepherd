"""Flow 5.2 - Broadcast a message to all drivers (admin, 3-step)."""

from __future__ import annotations

from app import keyboards, sessions, texts
from app.context import Ctx
from app.tg import send, send_dice


async def broadcast(ctx: Ctx, route: str | None) -> None:
    if route == "cmd_admin_broadcast":
        await sessions.set_state(ctx.chat_id, {"flow": "broadcast", "step": "awaiting_message"})
        await send(ctx, texts.BROADCAST_PROMPT)
        return

    if route == "broadcast_message":
        resp = await ctx.fleet.get("/users", params={"role": "driver"})
        drivers = resp.json() if resp.status_code == 200 else []
        chat_ids = [d["telegram_chat_id"] for d in drivers if d.get("telegram_chat_id")]
        await sessions.set_state(
            ctx.chat_id,
            {
                "flow": "broadcast",
                "step": "awaiting_confirm",
                "message": ctx.text,
                "recipients": chat_ids,
            },
        )
        await send(
            ctx,
            texts.BROADCAST_CONFIRM.format(count=len(chat_ids)),
            reply_markup=keyboards.broadcast_confirm(),
        )
        return

    if route == "broadcast_send":
        message = ctx.state.get("message", "")
        for chat in ctx.state.get("recipients", []):
            await ctx.bot.send_message(chat, message, parse_mode="HTML")
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.BROADCAST_SENT)
        await send_dice(ctx)
        return

    if route == "broadcast_cancel":
        await sessions.clear_state(ctx.chat_id)
        await send(ctx, texts.BROADCAST_CANCELLED)
        return
