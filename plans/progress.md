# Execution Progress: Telegram Bot

## Plan
- **Plan location**: plans/telegram-bot.md
- **Started**: 2026-06-21
- **Last updated**: 2026-06-21
- **Status**: in-progress

## Notes
- Git worktrees are forbidden in this project (user preference). Structural TDD
  (test-author isolation via worktree) is skipped for all tasks. Implementation
  proceeds against acceptance criteria directly.

## Tasks

| # | Task | Tests | Implementation | Status | Notes |
|---|------|-------|----------------|--------|-------|
| 01 | DB migration: bot_invite_tokens + users + bot_sessions | skipped | done | done | 0008_bot_tables.py |
| 02 | DB migration: extend accident_attachment_category_enum | skipped | done | done | 0009_accident_attachment_enum_ext.py |
| 03 | DB models: BotInviteToken, BotUser, BotSession in shepherd_db | skipped | done | done | models.py updated |
| 04 | Fleet API: GET /whoami | skipped | done | done | routers/bot.py |
| 05 | Fleet API: POST /bot-invite + POST /bot-invite/claim | skipped | done | done | routers/bot.py |
| 06 | Fleet API: PATCH /users/:id/role + GET /users + invite mgmt | skipped | done | done | routers/bot.py |
| 07 | n8n workflow: base router + unknown user / token claim | skipped | done | done | services/n8n/workflows/shepherd-telegram-bot.json |
| 08 | n8n: driver flows (clock in/out, vehicle, update, CSV, issue, accident) | skipped | done | done | all driver flows implemented (146-node workflow) |
| 09 | n8n: admin flows (attendance, summary, broadcast, update driver, maintenance) | skipped | done | done | all admin flows implemented incl. update-driver + maintenance |
| 10 | WebUI: invite panel on driver card + bot users table + pending invites | skipped | done | done | app/(admin)/bot/page.tsx, hooks/useBotManagement.ts, DriverCard |

## Current State
All 10 tasks complete. Follow-up pass done: fixed Main Router off-by-one wiring
bug, implemented the 6 remaining flows (my vehicle, attendance CSV, vehicle
issue, update details, update driver, maintenance), fixed n8n S3_BUCKET env var,
and added services/n8n/workflows/README.md documenting every node/flow.

## Test Artifacts
None (TDD skipped project-wide due to no-worktrees constraint).

## Completed Artifacts

| Task | Files |
|------|-------|
| — | — |

## Disputes
None.

## Failures
None.
