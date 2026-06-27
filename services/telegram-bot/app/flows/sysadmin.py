"""Feature 6 - System Admin: overview, Debug (Playground) + Customer-Live impersonation.

The operator's impersonation context is stashed in ``bot_sessions.state["impersonation"]``;
``router.dispatch`` rewrites whoami to the effective persona from it, so every existing
menu/feature/flow runs unchanged as that persona. This module only handles the
system-admin menu actions (overview / enter Debug / enter Live / exit) and the audit
trail; the audit POSTs always use a company-less system-admin caller carrying the
operator id (the effective context would be 403 on /sysadmin/*).
"""

from __future__ import annotations

from app import commands, keyboards, sessions, texts
from app.context import Ctx
from app.tg import send


def persona_label(imp: dict) -> str:
    if imp.get("role") == "admin":
        return texts.SA_PERSONA_ADMIN
    return imp.get("driver_name") or texts.SA_PERSONA_DRIVER


def banner(imp: dict) -> str:
    if imp.get("mode") == "live":
        return texts.SA_BANNER_LIVE.format(
            persona=persona_label(imp), company=imp.get("company_name", "")
        )
    return texts.SA_BANNER_DEBUG


async def audit(ctx: Ctx, imp: dict, action: str, detail: str | None = None) -> None:
    """Record a Customer-Live action. No-op for Debug (Playground is unaudited)."""
    if imp.get("mode") != "live":
        return
    caller = {"role": "admin", "impersonator": str(imp["operator_id"])}
    body = {
        "company_id": imp["company_id"],
        "effective_role": "company_admin" if imp["role"] == "admin" else "driver",
        "action": action,
    }
    if imp.get("effective_id"):
        body["effective_id"] = str(imp["effective_id"])
    if detail:
        body["detail"] = detail
    await ctx.fleet.post("/sysadmin/impersonation-audit", body, caller=caller)


async def _show_persona_menu(ctx: Ctx, imp: dict) -> None:
    """The persona's own menu, prefixed with the impersonation banner + an exit row."""
    await commands.apply(
        ctx.bot, ctx.chat_id, imp["role"], imp.get("attendance_enabled", True)
    )
    if imp["role"] == "admin":
        title, kb = texts.ADMIN_MENU_TITLE, keyboards.admin_menu()
    else:
        title = texts.DRIVER_MENU_TITLE
        kb = keyboards.driver_menu(imp.get("attendance_enabled", True))
    await send(ctx, f"{banner(imp)}\n\n{title}", reply_markup=keyboards.with_exit(kb))


async def _enter(ctx: Ctx, imp: dict, ack: str) -> None:
    await audit(ctx, imp, "start", detail="enter live session")
    await sessions.set_state(ctx.chat_id, {"impersonation": imp})
    await send(ctx, ack)
    await _show_persona_menu(ctx, imp)


async def sysadmin(ctx: Ctx, route: str | None) -> None:
    # Exit is the only action reachable while impersonating; everything else is
    # operator-only (the persona never sees a system-admin button).
    if route == "exit":
        await _exit(ctx)
        return
    if not ctx.is_system_admin:
        await send(ctx, texts.ACCESS_DENIED)
        return

    if route == "overview":
        await _overview(ctx)
    elif route == "debug_menu":
        await send(ctx, texts.SA_DEBUG_PICK, reply_markup=keyboards.sa_debug_pick())
    elif route == "debug_driver":
        await _debug_driver(ctx)
    elif route == "debug_admin":
        await _debug_admin(ctx)
    elif route == "live_start":
        await _live_start(ctx)
    elif route == "live_pick_company":
        await _live_pick_company(ctx)
    elif route == "live_pick_role":
        await _live_pick_role(ctx)
    elif route == "live_pick_driver":
        await _live_pick_driver(ctx)
    elif route == "live_pick_admin":
        await _live_pick_admin(ctx)


async def _overview(ctx: Ctx) -> None:
    resp = await ctx.fleet.get("/sysadmin/overview")
    companies = resp.json().get("companies", []) if resp.status_code == 200 else []
    if not companies:
        await send(ctx, f"{texts.SA_OVERVIEW_TITLE}\n\n{texts.SA_OVERVIEW_EMPTY}")
        return
    lines = [texts.SA_OVERVIEW_TITLE, ""]
    for c in companies:
        lines.append(
            texts.SA_OVERVIEW_LINE.format(
                name=c["name"],
                vehicles=c["vehicle_count"],
                drivers=c["driver_count"],
                events=c["open_event_count"],
                attendance=texts.SA_ON if c["attendance_enabled"] else texts.SA_OFF,
                drive=texts.SA_ON if c["gdrive_configured"] else texts.SA_OFF,
            )
        )
    await send(ctx, "\n".join(lines))


# --- Debug (Playground sandbox; unguarded + unaudited) ---


async def _debug_driver(ctx: Ctx) -> None:
    playground = ctx.whoami.get("playground_company_id")
    if not playground:
        await send(ctx, texts.SA_NO_PLAYGROUND)
        return
    resp = await ctx.fleet.get(f"/sysadmin/companies/{playground}/drivers")
    drivers = resp.json() if resp.status_code == 200 else []
    if not drivers:
        await send(ctx, texts.SA_NO_DRIVERS)
        return
    d = drivers[0]
    imp = {
        "mode": "debug",
        "role": "driver",
        "company_id": str(playground),
        "driver_id": d["driver_id"],
        "driver_name": d["full_name"],
        "operator_id": ctx.whoami.get("user_id"),
        "attendance_enabled": True,
    }
    await sessions.set_state(ctx.chat_id, {"impersonation": imp})
    await send(ctx, texts.SA_DEBUG_ACK.format(persona=texts.SA_PERSONA_DRIVER))
    await _show_persona_menu(ctx, imp)


async def _debug_admin(ctx: Ctx) -> None:
    playground = ctx.whoami.get("playground_company_id")
    if not playground:
        await send(ctx, texts.SA_NO_PLAYGROUND)
        return
    imp = {
        "mode": "debug",
        "role": "admin",
        "company_id": str(playground),
        "operator_id": ctx.whoami.get("user_id"),
        "attendance_enabled": True,
    }
    await sessions.set_state(ctx.chat_id, {"impersonation": imp})
    await send(ctx, texts.SA_DEBUG_ACK.format(persona=texts.SA_PERSONA_ADMIN))
    await _show_persona_menu(ctx, imp)


# --- Customer Live (real tenant; banner + audit) ---


async def _live_start(ctx: Ctx) -> None:
    resp = await ctx.fleet.get("/sysadmin/companies")
    companies = resp.json() if resp.status_code == 200 else []
    if not companies:
        await send(ctx, texts.SA_NO_COMPANIES)
        return
    await sessions.set_state(
        ctx.chat_id,
        {
            "flow": "sa_live",
            "step": "pick_company",
            "companies": {c["company_id"]: c["name"] for c in companies},
        },
    )
    items = [(c["name"], c["company_id"]) for c in companies]
    await send(
        ctx, texts.SA_LIVE_PICK_COMPANY, reply_markup=keyboards.pick_list(items, "sa_co_")
    )


async def _live_pick_company(ctx: Ctx) -> None:
    company_id = ctx.callback_data[len("sa_co_"):]
    name = ctx.state.get("companies", {}).get(company_id, "")
    await sessions.set_state(
        ctx.chat_id,
        {"flow": "sa_live", "step": "pick_role", "company_id": company_id, "company_name": name},
    )
    await send(
        ctx,
        texts.SA_LIVE_PICK_ROLE.format(company=name),
        reply_markup=keyboards.sa_live_role_pick(),
    )


async def _live_pick_role(ctx: Ctx) -> None:
    company_id = ctx.state["company_id"]
    name = ctx.state.get("company_name", "")
    if ctx.callback_data == "sa_role_driver":
        resp = await ctx.fleet.get(f"/sysadmin/companies/{company_id}/drivers")
        drivers = resp.json() if resp.status_code == 200 else []
        if not drivers:
            await send(ctx, texts.SA_NO_DRIVERS)
            return
        await sessions.set_state(
            ctx.chat_id,
            {
                "flow": "sa_live",
                "step": "pick_driver",
                "company_id": company_id,
                "company_name": name,
                "drivers": {d["driver_id"]: d["full_name"] for d in drivers},
            },
        )
        items = [(d["full_name"], d["driver_id"]) for d in drivers]
        await send(
            ctx,
            texts.SA_LIVE_PICK_DRIVER.format(company=name),
            reply_markup=keyboards.pick_list(items, "sa_drv_"),
        )
        return
    # Admin persona: pick a specific company_admin for the audit record (or enter
    # directly when the company has none).
    resp = await ctx.fleet.get(f"/sysadmin/companies/{company_id}/admins")
    admins = resp.json() if resp.status_code == 200 else []
    if not admins:
        await _enter(
            ctx,
            {
                "mode": "live",
                "role": "admin",
                "company_id": company_id,
                "company_name": name,
                "operator_id": ctx.whoami.get("user_id"),
                "attendance_enabled": True,
            },
            texts.SA_LIVE_ACK.format(persona=texts.SA_PERSONA_ADMIN, company=name),
        )
        return
    await sessions.set_state(
        ctx.chat_id,
        {
            "flow": "sa_live",
            "step": "pick_admin",
            "company_id": company_id,
            "company_name": name,
        },
    )
    items = [(a.get("name") or a["email"], a["user_id"]) for a in admins]
    await send(
        ctx,
        texts.SA_LIVE_PICK_ADMIN.format(company=name),
        reply_markup=keyboards.pick_list(items, "sa_adm_"),
    )


async def _live_pick_driver(ctx: Ctx) -> None:
    driver_id = ctx.callback_data[len("sa_drv_"):]
    name = ctx.state.get("company_name", "")
    driver_name = ctx.state.get("drivers", {}).get(driver_id)
    imp = {
        "mode": "live",
        "role": "driver",
        "company_id": ctx.state["company_id"],
        "company_name": name,
        "driver_id": driver_id,
        "driver_name": driver_name,
        "effective_id": driver_id,
        "operator_id": ctx.whoami.get("user_id"),
        "attendance_enabled": True,
    }
    await _enter(
        ctx, imp, texts.SA_LIVE_ACK.format(persona=persona_label(imp), company=name)
    )


async def _live_pick_admin(ctx: Ctx) -> None:
    admin_id = ctx.callback_data[len("sa_adm_"):]
    name = ctx.state.get("company_name", "")
    imp = {
        "mode": "live",
        "role": "admin",
        "company_id": ctx.state["company_id"],
        "company_name": name,
        "effective_id": admin_id,
        "operator_id": ctx.whoami.get("user_id"),
        "attendance_enabled": True,
    }
    await _enter(
        ctx, imp, texts.SA_LIVE_ACK.format(persona=texts.SA_PERSONA_ADMIN, company=name)
    )


async def _exit(ctx: Ctx) -> None:
    imp = ctx.impersonation
    if imp is None:
        # /exit with nothing to leave - just show the caller's normal menu.
        from app.flows.access import menu

        await menu(ctx, None)
        return
    await audit(ctx, imp, "stop", detail="exit live session")
    await sessions.exit_impersonation(ctx.chat_id)
    # Drop any reply keyboard the persona left up (e.g. accident share-location) before
    # the inline system-admin menu, which would otherwise sit on top of a stale keyboard.
    await send(ctx, texts.SA_EXITED, reply_markup=keyboards.remove())
    await send(ctx, texts.SYSADMIN_MENU_TITLE, reply_markup=keyboards.sysadmin_menu())
