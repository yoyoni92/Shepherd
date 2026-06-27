"""Access control + menus: phone enrollment, access denied, role menus."""

from __future__ import annotations

from app import commands, keyboards, texts
from app.context import Ctx
from app.flows.sysadmin import banner
from app.tg import send


async def menu(ctx: Ctx, route: str | None) -> None:
    # System Admin, not impersonating: the operator's own cross-company menu.
    if ctx.is_system_admin and not ctx.impersonation:
        await send(ctx, texts.SYSADMIN_MENU_TITLE, reply_markup=keyboards.sysadmin_menu())
        return
    await commands.apply(ctx.bot, ctx.chat_id, ctx.role, ctx.attendance_enabled)
    if ctx.role == "admin":
        title, kb = texts.ADMIN_MENU_TITLE, keyboards.admin_menu()
    else:
        title, kb = texts.DRIVER_MENU_TITLE, keyboards.driver_menu(ctx.attendance_enabled)
    # While impersonating, prefix the persistent banner + offer the exit control.
    if ctx.impersonation:
        title = f"{banner(ctx.impersonation)}\n\n{title}"
        kb = keyboards.with_exit(kb)
    await send(ctx, title, reply_markup=kb)


async def access_denied(ctx: Ctx, route: str | None) -> None:
    await send(ctx, texts.ACCESS_DENIED)


async def enroll(ctx: Ctx, route: str | None) -> None:
    """No invites: an unknown user shares their phone and we match it to a role.

    The contact-share is detected by the router (verified phone) regardless of
    session state, so there's nothing to stash between the two steps.
    """
    if route == "request_phone":
        # A driver who typed text (not the initial /start) is trying to send the number
        # manually - nudge them to the button instead of repeating the same prompt.
        typed = ctx.text and not ctx.is_start
        msg = texts.CLAIM_USE_BUTTON if typed else texts.CLAIM_REQUEST_PHONE
        await send(ctx, msg, reply_markup=keyboards.request_contact())
        return

    if route == "enroll_with_phone":
        resp = await ctx.fleet.enroll(ctx.chat_id, ctx.contact_phone)
        if resp.status_code == 200:
            role = resp.json().get("role")
            await commands.apply(ctx.bot, ctx.chat_id, role)
            kb = keyboards.admin_menu() if role == "admin" else keyboards.driver_menu()
            await send(ctx, texts.WELCOME.get(role, texts.WELCOME_DRIVER), reply_markup=kb)
        else:
            await send(ctx, texts.NOT_AUTHORIZED)
