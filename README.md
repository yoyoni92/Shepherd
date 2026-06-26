# Shepherd

AI-powered vehicle fleet management.

Design & build plans: [`../plans/`](../plans/README.md) (design) and
[`../plans/implementation/`](../plans/implementation/00-overview.md) (TDD build plans).

## Layout

```
libs/             shared contracts (pydantic models + provider interfaces)
db/               Postgres schema (models = source of truth) + bootstrap.sql + seed
services/         fleet-api, telegram-bot, webui
tests/e2e/        cross-system integration tests (telegram-bot vs live stack)
plans/            design & implementation plans
```

## Dev setup

- Python **3.12** (services), managed with **Poetry**. WebUI: **Node.js 22** + npm.
- Per package: `poetry env use python3.12 && poetry install && poetry run pytest`.
- Cross-system integration tests: `make up` then `make e2e` (drives the telegram-bot
  against the live Fleet API + Postgres; see [`tests/e2e/`](tests/e2e/README.md)).

## Status

The active stack is three services on Postgres: **fleet-api**, **telegram-bot**, **webui**.
(Earlier iterations carried a doc-ingest pipeline and a chat/RAG stack; those were removed.
A fresh Google-Drive-files RAG is planned next.)

`services/fleet-api`: sole Postgres writer and tool layer (SQLAlchemy ORM, full OpenAPI
docs). Also owns file uploads - `POST /files` stores bytes in Google Drive and returns a
public link, which callers persist as `file_url`.

`services/webui`: Next.js 15 + Tailwind + TanStack Query admin console - login, KPI
dashboard, entity CRUD (vehicles, drivers, customers, events, accidents, attendance,
maintenance types), Config editor, Bot Management (invite panel on driver card, bot users
table, pending invites), and system health. Stack: Next.js App Router, next-auth
credentials, Zod, MSW, Vitest + RTL, Playwright e2e. Served at port 3000.

`services/telegram-bot`: phone-enrolled Hebrew Telegram bot on aiogram 3 with long-polling
(no public HTTPS / tunnel). Driver flows (clock in/out, accident, vehicle issue, update
details, attendance CSV, my vehicle) and admin flows (attendance, broadcast, fleet summary,
update driver, maintenance, document scan). Fleet API is the only tool layer; multi-step
state lives in `bot_sessions`. Two LLM touches: accident description by **voice (Whisper)
or text**, and an admin **document scan** (Gemini vision -> confirm -> apply). Accident
media is uploaded via Fleet API to Google Drive, never run through an LLM. **Access (no
invites):** an active driver auto-gets the driver role; admins + temporary (time-limited)
roles come from `bot_authorizations`. The user shares their phone once and is matched by
`POST /bot-enroll`; expired roles are swept by pg_cron. Role management via WebUI.
