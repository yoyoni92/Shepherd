# Impl: Feature 6 - System Admin (Telegram)

**Status**: done (fleet-api 159 · telegram-bot 65 · webui 113, all green)
**Epic**: extends `plans/epics/multi-tenancy-and-company-admin.md`
**Spec/ADR**: `CONTEXT.md` (personas) + `docs/adr/0001-system-admin-telegram-impersonation.md`
**Mode**: ponytail (full) + TDD
**Depends on**: Features 1-5

## Goal

A System Admin persona in the Telegram bot with three capabilities: read-only
**system overview**, a sandbox **debug mode** (Playground company), and guarded
**customer live mode** (act as a real company's admin/driver, audited).

## Decisions (grilled)

- **Identity**: `app_users.is_system_admin` (default false) + `phone_number` +
  `telegram_chat_id`. Bot recognizes the operator at whoami via telegram_chat_id
  (system-admin path wins). No tenant `users` row for the operator.
- **Playground**: one seeded built-in company, `companies.is_internal=true`, with
  mock drivers/vehicles + a company_settings row. Excluded from customer lists +
  overview counts.
- **Customer Live lists**: admins = company_admin `app_users` of the company;
  drivers = the company's `drivers`.
- **Guardrails**: Debug = unguarded/unaudited. Live = persistent banner +
  confirm-on-destructive (broadcast-to-all, delete, bulk) + audit.
- **Audit**: `CallerContext.impersonator` + `impersonation_audit` table written by
  fleet-api (session start/stop + confirmed writes). Queryable now; webui viewer later.
- **Trust**: fleet-api trusts the bot internal token; no impersonator re-verify yet.
- **Scope**: Telegram only (no webui act-as). Webui only adds is_system_admin +
  phone provisioning on the Access tab.

## Backend slices (TDD) - DOING NOW

- [x] **D1** db: `app_users.is_system_admin/phone_number/telegram_chat_id`,
      `companies.is_internal`, `CallerContext.impersonator`, `impersonation_audit` table.
- [x] **D2** whoami: system-admin path (app_users by telegram_chat_id, is_system_admin)
      returns is_system_admin + role admin + null company; enroll links telegram_chat_id
      by phone match to an is_system_admin app_user (precedence over driver/auth).
- [x] **D3** system overview endpoint (system-admin only): per-company counts/health,
      excluding is_internal companies.
- [x] **D4** live-mode list endpoints: real companies (exclude is_internal); a company's
      company_admin app_users; a company's drivers. (reuse/extend existing where possible)
- [x] **D5** audit: fleet-api writes impersonation_audit on a start/stop endpoint and on
      confirmed writes carrying CallerContext.impersonator (live, non-internal company only).
- [x] **D6** seed: Playground company (is_internal) + mock drivers/vehicles +
      company_settings; mark the seeded admin app_user is_system_admin + phone.

## Bot slices - AFTER backend
- [x] whoami exposes is_system_admin -> render the system-admin menu (overview / debug / live).
- [x] debug mode: pick driver|admin playground -> impersonation context (company=playground); unguarded.
- [x] customer live: pick company -> pick admin|driver -> impersonation context + banner + audit start.
- [x] per-update client builds the effective caller context (+ impersonator) from session state.
- [x] confirm-on-destructive in live; exit clears context (+ audit stop).
- [x] relabel the existing bot "admin" menu to "מנהל חברה".

## Webui slice - AFTER
- [x] Access tab: is_system_admin toggle + phone field on app-user create/edit.
  - 2026-06-28: Access create form gains a "מנהל מערכת" checkbox (forces role=admin,
    company_id null, hides company/role selectors) + phone field; list shows a
    system-admin badge and the phone column. AppUserRead/Create/Update Zod + types carry
    is_system_admin/phone_number. webui `npm test` 113 pass; typecheck/lint/build clean.

## e2e - AFTER
- [ ] (bot pytest covers flows) + a webui e2e that an Access app-user can be marked system admin.

## Verify

`cd services/fleet-api && poetry run pytest -q` ; `cd services/telegram-bot && poetry run pytest -q` ;
`cd services/webui && npm test`.

## Running log / decisions

- 2026-06-27: grilled (grill-with-docs). CONTEXT.md personas + ADR 0001 written. Three
  capabilities (overview/debug/live); two flag columns (app_users.is_system_admin,
  companies.is_internal); Live impersonation audited via CallerContext.impersonator.
- 2026-06-27: backend D1-D6 done (db + fleet-api, no bot/webui). New `/sysadmin/*`
  router gated by company-less admin (role==admin & company_id is None) since
  CallerContext has no is_system_admin; whoami/enroll give the system-admin path
  precedence (app_user by telegram_chat_id / phone over tenant matches). `list_companies`
  now excludes internal by default. Seed adds the Playground (is_internal) + flags the
  admin app_user. fleet-api `pytest -q`: 158 passed; ruff clean on touched files.
- 2026-06-28: bot slice done. `Ctx.is_system_admin`/`Ctx.impersonation`; `router.dispatch`
  rewrites whoami to the effective persona from `state["impersonation"]` and binds the
  per-update `FleetClient` to the effective company + `impersonator` (fleet.py
  `as_impersonator`). New `flows/sysadmin.py`: overview (system-admin context),
  Debug (Playground, unaudited), Customer-Live picker (company -> role -> driver/admin)
  with start/stop/write audits posted via a company-less `{role:admin, impersonator}`
  caller. Banner + exit on impersonated menus; "admin" menu relabelled "מנהל חברה".
  Impersonation is sticky across flow `set_state`/`clear_state` (sessions.py); `exit`
  drops it. Tiny fleet-api add: whoami returns `playground_company_id`. Destructive =
  broadcast-to-all (its existing yes/no confirm is the guard; live send -> write audit).
  telegram-bot `pytest -q`: 65 passed. fleet-api `pytest -q`: 159 passed. ruff: no new
  findings on touched files.
