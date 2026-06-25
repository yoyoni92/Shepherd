"""Access control + menus: invite claim, access denied, role menus."""

from __future__ import annotations

from app import commands, keyboards, sessions, texts
from app.context import Ctx
from app.tg import send


async def menu(ctx: Ctx, route: str | None) -> None:
    await commands.apply(ctx.bot, ctx.chat_id, ctx.role)
    if ctx.role == "admin":
        await send(ctx, texts.ADMIN_MENU_TITLE, reply_markup=keyboards.admin_menu())
    else:
        await send(ctx, texts.DRIVER_MENU_TITLE, reply_markup=keyboards.driver_menu())


async def access_denied(ctx: Ctx, route: str | None) -> None:
    await send(ctx, texts.ACCESS_DENIED)


async def invite_claim(ctx: Ctx, route: str | None) -> None:
    if route == "claim_request_phone":
        await sessions.set_state(ctx.chat_id, {"flow": "invite_claim", "token": ctx.start_token})
        await send(ctx, texts.CLAIM_REQUEST_PHONE, reply_markup=keyboards.request_contact())
        return

    if route == "claim_with_phone":
        token = ctx.state.get("token")
        resp = await ctx.fleet.claim_invite(token, ctx.chat_id, ctx.contact_phone)
        await sessions.clear_state(ctx.chat_id)
        if resp.status_code == 200:
            role = resp.json().get("role")
            await commands.apply(ctx.bot, ctx.chat_id, role)
            kb = keyboards.admin_menu() if role == "admin" else keyboards.driver_menu()
            await send(ctx, texts.CLAIM_WELCOME, reply_markup=kb)
        elif resp.status_code == 403:
            await send(ctx, texts.CLAIM_PHONE_MISMATCH)
        else:
            await send(ctx, texts.CLAIM_INVALID)
