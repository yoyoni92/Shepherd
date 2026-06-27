# Impl: Feature 3 - Bot Tenancy

**Status**: done (138 fleet-api tests; 53 telegram-bot tests; ruff clean for introduced lines)
**Epic**: `plans/epics/multi-tenancy-and-company-admin.md` (Feature 3)
**Mode**: ponytail (full) + TDD
**Depends on**: Feature 1 (hard); Feature 2 (webui Bot-tab gating)

## Goal

Make the Telegram bot multi-tenant. Set `company_id` on bot writers (then flip the
two bot columns NOT NULL), return company from `whoami`, make `admin_ctx()` and all
bot flows company-aware, and expose the Bot tab to company admins scoped to their
company.

## Ponytail guardrails (provisional)

- Bot user company derives from the matched driver; authorization company derives
  from the inviting caller. No new resolution layer.
- `admin_ctx()` -> carry the acting company_id where one exists; system-wide bot
  calls stay company-less only where genuinely cross-company.
- Don't refactor the 13 flows wholesale - thread company_id through the one shared
  caller-context builder so each flow inherits it (root-cause, not per-flow patch).

## TDD slices (to refine at start)

fleet-api (`services/fleet-api/tests`):
- [x] enroll sets `company_id` from the matched driver; columns now NOT NULL.
- [x] `create_bot_authorization` sets `company_id` from caller.
- [x] `whoami` returns the user's `company_id`.
- [x] `MANAGE_BOT_USERS`/`MANAGE_BOT_INVITES`: company_admin scoped, admin across all.
- [x] enrollment matches phone within the correct company (guards auto-enroll-by-phone).

telegram-bot (`services/telegram-bot/tests`):
- [x] a bot flow call carries the enrolled user's company_id (one representative flow).

webui:
- [x] Bot tab visible+scoped for company_admin (already no `allowedRoles` -> visible to
  all logged-in roles incl. company_admin; F2 route gating + proxy scope it). No change.

## Verify command

`cd services/fleet-api && pytest -q` ; `cd services/telegram-bot && pytest -q`.

## Running log / decisions

- 2026-06-26: Implemented bot tenancy (TDD). Backend: `find_enrollment_by_phone` now
  resolves + returns the company (driver's company for a driver match, the
  authorization's company otherwise); `enroll_bot_user` + `create_bot_authorization`
  write it (the latter scopes its "one per phone" supersede to the same company so it
  can't delete another tenant's grant); `whoami`/`BotWhoamiResponse` return
  `company_id`; bot router list/create/update/delete pass `caller.company_id` and
  `assert_company` guards role-change + invite-revoke against cross-tenant access;
  matrix flips `MANAGE_BOT_USERS`/`MANAGE_BOT_INVITES` to allow company_admin (scoped
  by repo filters + assert_company); both bot columns flipped NOT NULL. Bot service:
  `FleetClient` gains a bound `company_id` + `for_company()`; `admin_ctx`/`driver_ctx`
  carry it; `dispatch` binds the per-update client to `whoami["company_id"]` so every
  flow call is scoped with zero per-flow churn; `Ctx.company_id` property added.
  Webui: `/bot` nav already had no `allowedRoles` (visible to all logged-in roles), so
  company_admin sees it and the F2 proxy scopes it - no change.
- Verify: `fleet-api` 138 passed; `telegram-bot` 53 passed. ruff: no new lint from the
  changed lines (only a pre-existing `enroll` docstring E501 remains in `fleet.py`).
