# Shepherd

AI-powered vehicle fleet management.

Design & build plans: [`../plans/`](../plans/README.md) (design) and
[`../plans/implementation/`](../plans/implementation/00-overview.md) (TDD build plans).

## Layout

```
libs/             shared packages: shepherd-contracts (pydantic models + provider interfaces), shepherd-config (typed config loader)
db/               Postgres schema (models = source of truth) + bootstrap.sql + seed
services/         fleet-api, telegram-bot, webui
tests/e2e/        cross-system integration tests (telegram-bot vs live stack)
plans/            design & implementation plans
deploy/           production runbook: pull-only compose, deploy.sh, config/env templates
config.example.toml  central config template (DB URL + company-to-schema map)
```

## Configuration

The DB connection string and the company-to-schema map live in `config.toml` (gitignored).
Copy `config.example.toml`, fill in secrets, and point the services at it:

```
SHEPHERD_CONFIG=/path/to/config.toml
```

The `shepherd_config` package (`libs/shepherd_config`) loads this file at startup with
`${VAR}` env interpolation. Secret values stay in the environment; the TOML file is safe
to commit without credentials.

Tenant isolation uses schema-per-tenant: each company's domain tables live in its own
Postgres schema, routed via `schema_translate_map`. `company_id` row scoping is also
enforced and is load-bearing when companies share a schema.

## Dev setup

- Python **3.12** (services), managed with **Poetry**. WebUI: **Node.js 22** + npm.
- Per package: `poetry env use python3.12 && poetry install && poetry run pytest`.
- Cross-system integration tests: `make up` then `make e2e` (drives the telegram-bot
  against the live Fleet API + Postgres; see [`tests/e2e/`](tests/e2e/README.md)).
- Production deploy: see [`deploy/README.md`](deploy/README.md) - pulls pre-built Docker
  Hub images; no git clone needed on the server.

## CI

GitHub Actions (`.github/workflows/ci.yml`): path-filtered per-package quality gates
(lint/typecheck/test via the Makefile, one leg per changed package) on every push and
pull request; build and push all 5 service images to Docker Hub on merge to `main`.
Required GitHub config: secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`, var
`DOCKERHUB_ORG`.

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
