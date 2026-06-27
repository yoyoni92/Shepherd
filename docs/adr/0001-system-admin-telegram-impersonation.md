# 1. System-admin impersonation in the Telegram bot

Date: 2026-06-27
Status: Accepted

## Context

The platform operator (System Admin) needs to debug and operate companies from
the Telegram bot: experience the driver and company-admin flows, and act on a
real customer's behalf to investigate issues. Tenant data is strictly isolated
(every row carries a `company_id`), so a System Admin acting inside a tenant is
deliberately crossing the isolation boundary.

Two risks pull against the requirement: (1) doing real work as someone else can
corrupt a tenant's data, and (2) the operator wants the genuine "feeling" of the
persona, so heavy friction defeats the purpose.

## Decision

Provide three System-Admin capabilities, with the guardrail matched to the blast
radius of each:

- **System overview** - read-only, cross-company. The bot calls fleet-api with a
  company-less admin context. No mutation, no audit.
- **Debug mode** - act as a driver or company admin inside a single built-in
  **Playground company** (`companies.is_internal = true`, mock data). Because no
  real tenant is touched, it is unguarded and unaudited.
- **Customer Live mode** - select a real customer, then act as one of its
  company-admin `app_users` or one of its drivers. Guarded by a persistent
  "acting as" banner, a confirmation on destructive actions (broadcast-to-all,
  delete, bulk), and a persisted audit trail.

Mechanics: the System-Admin identity is an `app_user` flagged
`is_system_admin = true` (linked to Telegram via `phone_number` +
`telegram_chat_id`). The act-as context lives in `bot_sessions.state`. While
impersonating, the bot sets `CallerContext.impersonator` to the operator's id;
fleet-api records Customer-Live sessions and confirmed writes to an
`impersonation_audit` table. fleet-api trusts the bot's internal token (the bot
authoritatively resolves system-admin status); it does not re-verify the
impersonator.

## Alternatives considered

- **Read-only impersonation everywhere.** Safest, but the operator explicitly
  needs to *operate*, not just inspect. Rejected.
- **Confirm every write.** Safe but breaks the "feeling" of being the persona
  during real work. Rejected in favour of confirm-only-on-destructive.
- **Operate directly on real tenants for all debugging** (no Playground).
  Rejected: most debugging is flow-shape exploration that should never risk real
  data; the Playground sandbox covers it.
- **A separate system-admin identity disconnected from the web login.** Rejected:
  reusing the `app_user` keeps one operator identity across web and bot.

## Consequences

- Cross-tenant writes are possible by design; the audit trail is the
  accountability control, so it must be reliable.
- `app_users` gains `is_system_admin`, `phone_number`, `telegram_chat_id`;
  `companies` gains `is_internal`; `CallerContext` gains `impersonator`; a new
  `impersonation_audit` table is added.
- The Playground company must be seeded with mock data and kept out of
  customer-facing lists and overview counts.
- fleet-api trusting the bot token is acceptable while the bot is the only
  impersonation entry point; if web act-as is added later, fleet-api should
  verify the impersonator is a real system admin.
