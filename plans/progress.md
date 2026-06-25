# Execution Progress: Telegram Bot

## Plan
- **Plan location**: plans/telegram-bot.md
- **Started**: 2026-06-21
- **Last updated**: 2026-06-25
- **Status**: complete (native aiogram service)

## Notes
- Git worktrees are forbidden in this project (user preference). Structural TDD
  (test-author isolation via worktree) is skipped for all tasks. Implementation
  proceeds against acceptance criteria directly.
- The bot was first built as an n8n workflow, then **rewritten 1:1 as a native
  `services/telegram-bot` (aiogram 3, long-polling)**. n8n and its localtunnel
  sidecar were removed from `docker-compose.yml`; `services/n8n/workflows/*`
  were deleted. DB schema and Fleet API contracts were unchanged by the rewrite.
- **Access reworked (2026-06):** invite tokens replaced by **phone-match
  auto-enrollment** - active drivers auto-get the driver role; admins + temporary
  (time-limited) roles in a new `bot_authorizations` table; `POST /bot-enroll`
  matches the shared phone; expired/deactivated access denied at `whoami` and
  swept by pg_cron. Alembic removed - `db/models.py` is the schema source
  (`create_all` + `bootstrap.sql`); WebUI invite UI replaced by an authorizations
  panel + plain bot link.

## Tasks

| # | Task | Tests | Implementation | Status | Notes |
|---|------|-------|----------------|--------|-------|
| 01 | DB migration: bot_invite_tokens + users + bot_sessions | skipped | done | done | 0008_bot_tables.py |
| 02 | DB migration: extend accident_attachment_category_enum | skipped | done | done | 0009_accident_attachment_enum_ext.py |
| 03 | DB models: BotInviteToken, BotUser, BotSession in shepherd_db | skipped | done | done | models.py |
| 04 | Fleet API: GET /whoami | skipped | done | done | routers/bot.py |
| 05 | Fleet API: POST /bot-invite + POST /bot-invite/claim | skipped | done | done | routers/bot.py (phone-verified claim, 0011/0012) |
| 06 | Fleet API: PATCH /users/:id/role + GET /users + invite mgmt | skipped | done | done | routers/bot.py |
| 07 | Bot: routing core (normalize -> whoami -> route_decision) | done | done | done | app/main.py, app/router.py |
| 08 | Bot: driver flows (clock, vehicle issue, accident, update details, CSV, my vehicle) | done | done | done | app/flows/*.py |
| 09 | Bot: admin flows (attendance, summary, broadcast, update driver, maintenance, doc scan) | done | done | done | app/flows/*.py |
| 10 | WebUI: invite panel on driver card + bot users table + pending invites | skipped | done | done | app/(admin)/bot/page.tsx, hooks/useBotManagement.ts, DriverCard |

## Current State
Native aiogram service complete. Single dispatch pipeline; flows are stateless
handlers keyed by `(feature, route)`; multi-step state in `bot_sessions` (the
bot's only direct DB access). Fleet API is the sole tool layer. Two LLM touches:
accident description via OpenAI Whisper (`app/stt.py`), admin document scan via
Gemini vision (`app/vision.py`). Accident media is stored to S3, never run
through an LLM. Tests in `tests/test_flows.py` (router gating, driver/admin
flows, vision, sendDice flourish) with Fleet API mocked via respx.

## Test Artifacts
`services/telegram-bot/tests/test_flows.py` - flow + router behavior, Fleet API
mocked (respx), bot + sessions faked (`tests/conftest.py`).

## Disputes
None.

## Failures
None.
