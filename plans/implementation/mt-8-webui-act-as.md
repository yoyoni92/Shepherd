# Impl: Feature 8 - WebUI act-as company admin

**Status**: in-progress
**Mode**: ponytail + TDD + frontend-design (existing dark/RTL system)
**Depends on**: Features 1-7 (esp. F6 impersonation: CallerContext.impersonator + /sysadmin/impersonation-audit)
**Refs**: docs/adr/0001-system-admin-telegram-impersonation.md (web act-as was deferred there)

## Goal

The webui counterpart of F6's act-as: a system admin picks a real company and
operates the **company-admin console** for it (company-admin nav, scoped data),
with a persistent banner, an exit, and an audit trail. Full operate (match
Telegram). Company-admin only (drivers use the bot).

## Decisions (grilled)

- **Scope**: full operate (real actions), banner + audit (reuse F6
  `impersonation_audit`). Company-admin only.
- **Entry**: a per-company **"Act as company admin"** button on the Companies page.
- **Backend**: NONE required - `company_admin` context + `CallerContext.impersonator`
  + the `/sysadmin/impersonation-audit` endpoint already exist. fleet-api keeps
  trusting the webui proxy's internal token (same model as the bot); impersonator
  re-verification noted as future hardening per ADR 0001.

## Mechanics

- Act-as state in an httpOnly-not-required cookie `act_as_company` = the target
  company_id (only honored when the session role is `admin`).
- **Proxy** (`app/api/fleet/[...path]/route.ts`): when `act_as_company` is set and
  session role is admin, build `X-Caller-Context = {role:'company_admin',
  company_id:<act_as>, impersonator:<session user id>}` (overrides the normal
  admin/switcher context). Best-effort: on a mutating request (POST/PATCH/DELETE)
  while acting-as, also POST an audit `write` row.
- **Nav**: while acting-as, filter as `company_admin` (hide Companies/Access/
  Config/Health) and gate attendance by the act-as company's feature flags
  (fetched on enter, stored in the act-as state/cookie).
- **Banner**: persistent "פועל כמנהל חברה · <company>" with an exit; entering shows
  a one-time acknowledgement ("actions are real"). Exit clears the cookie.
- **Audit**: a webui server route posts start/stop to fleet-api
  `/sysadmin/impersonation-audit` using a SYSTEM-ADMIN context ({role:'admin',
  impersonator:<id>}, no company) - the act-as (company_admin) context would 403
  that endpoint, exactly like the bot.
- The Topbar **company switcher** is hidden while acting-as (context is fixed).

## Slices (TDD)
- [x] **F1** act-as cookie + proxy caller-context (admin + cookie -> company_admin + impersonator).
- [x] **F2** Companies page: "Act as" button per row -> set cookie + enter (land on /dashboard).
- [x] **F3** nav filters as company_admin while acting-as; system tabs hidden; attendance per the act-as company's flags.
- [x] **F4** persistent banner + entry ack + exit (clear cookie, back to /companies).
- [x] **F5** audit start/stop via a webui server route -> /sysadmin/impersonation-audit (system-admin context); best-effort per-write audit in the proxy.

## Verify
`cd services/webui && npm test` (+ build/typecheck/lint); Playwright e2e (enter act-as -> company-admin nav, no system tabs, banner; exit -> back).

## Running log / decisions
- 2026-06-28: grilled. Full operate, per-company "Act as" button, reuse F6 audit; no backend change.
- 2026-06-28: F1-F5 implemented. Two cookies (`act_as_company` id for the proxy +
  `act_as` JSON name/flags for nav/banner). Act-as state is read server-side in the
  (admin) layout and threaded through Shell -> Sidebar/Topbar/Banner (no hydration
  flash); enter/exit hard-navigate (window.location) so middleware + layout + proxy
  re-read fresh. `buildCallerContext` gained an `actAs` arg (admin -> company_admin +
  impersonator). Audit goes through `lib/audit.ts` (system-admin caller, no company)
  used by both the new `/api/impersonation-audit` route (start/stop, guarded to admin
  sessions) and the Fleet proxy (best-effort per-write, fire-and-forget). nav.ts
  unchanged - existing `filterNav(role='company_admin', actAs.feature_flags)` already
  hides system tabs and gates attendance. Tests: callerContext act-as, actAs cookie
  round-trip, audit context/body, nav-while-acting-as. npm test/typecheck/lint/build
  all green.
