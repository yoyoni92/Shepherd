# Shepherd

AI-powered vehicle fleet management. Conversational AI agent: **Moshes**.

Design & build plans: [`../plans/`](../plans/README.md) (design) and
[`../plans/implementation/`](../plans/implementation/00-overview.md) (TDD build plans).

## Layout

```
libs/             shared contracts (pydantic models + provider interfaces)
db/               Postgres schema, migrations, seed           [migrations 0001-0009]
services/         fleet-api, channel-gateway, doc-extractor,
                  image-analyser, rag, langgraph-agent,
                  guardrails, webui, telegram-bot
plans/            design & implementation plans
```

## Dev setup

- Python **3.12** (services), managed with **Poetry**. WebUI: **Node.js 22** + npm.
- Per package: `poetry env use python3.12 && poetry install && poetry run pytest`.

## Status

Phase 1 (foundation) complete: `libs/` contracts, `db/` schema/migrations, and
`services/fleet-api` (85 tests, SQLAlchemy ORM, full OpenAPI docs) are done.

`services/channel-gateway` complete: Telegram + webapp inbound, S3 media upload,
n8n forward, identity binding, outbound send, WhatsApp seam (33 tests, 93% coverage).

`services/doc-extractor` complete: Bedrock + Gemini vision extractors, provider factory,
reconcile-by-plate -> Fleet API, eval harness (10 fixtures, prompt V1), FastAPI wrapper
(38 tests, 94% coverage).

`services/rag` complete: vehicle-profile builder, multilingual embeddings
(paraphrase-multilingual-MiniLM-L12-v2), Chroma vector index, hard ownership filter,
LangChain/Claude Sonnet generator, POST /query endpoint, prompt log V1-V5
(29 tests, 91% coverage).

`services/langgraph-agent` complete: LangGraph StateGraph (planner -> tool-exec ->
synthesiser), Fleet API + RAG tool wrappers with caller-context forwarding, 403 surfaces
as refusal, injectable planner/synthesiser for deterministic tests, tool-description
prompt log V1-V5 (surface #2), POST /agent/run endpoint (24 tests, 85% coverage).

`services/guardrails` complete: deterministic auth + language pre-checks
(channel_identities + langdetect), Guardrails AI topic + grounding rails behind a
swappable GuardrailProvider Protocol (Bedrock stub included), POST /check/input +
POST /check/output, prompt log V1-V5 (surface #4), 0% FP on valid fleet set
(32 tests, 90% coverage).

`services/webui` complete: Next.js 15 + Tailwind + TanStack Query admin console
(login, KPI dashboard, Fleet Chat, Ollama Assistant, Upload, Config editor, Review Queue,
Bot Management - invite panel on driver card, bot users table, pending invites).
DB-blind assistant enforced at network + ESLint module-boundary level.
Deviation from Gradio/Streamlit noted: modern React SPA satisfies rubric "app.py or equivalent".
Stack: Next.js App Router, next-auth credentials, Zod, MSW, Vitest + RTL, Playwright e2e.
Served at port 3000.

`services/telegram-bot` (replaces n8n): invite-only Hebrew Telegram bot built on
aiogram 3 with long-polling (no public HTTPS / tunnel). Ports the 12 flows 1:1 -
driver (clock in/out, accident, vehicle issue, update details, attendance CSV, my
vehicle) and admin (attendance, broadcast, fleet summary, update driver, maintenance,
document scan). Fleet API is the only tool layer; multi-step state lives in
`bot_sessions`. Two LLM touches: accident description by **voice (Whisper) or text**,
and an admin **document scan** (Gemini vision -> confirm -> apply). Accident media is
stored as S3 attachments, never run through an LLM. Access controlled via one-time
invite tokens; role management via WebUI. Fleet API endpoints: `GET /whoami`,
`POST /bot-invite`, `POST /bot-invite/claim`, `PATCH /users/:id/role`. DB tables:
`users`, `bot_invite_tokens`, `bot_sessions` (migrations 0008-0009).
