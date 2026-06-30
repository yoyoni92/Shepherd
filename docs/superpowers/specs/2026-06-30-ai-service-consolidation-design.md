# AI Service: Consolidation, Sanity Check, DB Agent, and Per-Company RAG

Date: 2026-06-30
Status: Approved (design)

## Summary

Introduce a dedicated `ai-service` that owns every AI/LLM interaction in Shepherd, and
grow it across four capabilities:

1. **Consolidation + sanity check** - move the existing Whisper STT and Gemini
   doc-vision out of the bot into `ai-service`, and add an accident-description sanity
   check (the originating request).
2. **NL->DB agent** - convert a user prompt into a proper search over Shepherd data via
   Gemini function-calling against Fleet API's existing read endpoints.
3. **Per-company RAG agent** - answer questions about a company's documents (the planned
   Google-Drive-files RAG), scoped per company.

All capabilities live in one service; delivery is phased (see Phasing). The bot and the
WebUI call `ai-service` over HTTP. After Phase 1 the bot holds no LLM provider keys.

## Motivation

- The user wants a single service that "covers our AI", since more AI capabilities are
  coming.
- The originating request: after the accident description is resolved (voice
  transcribed, or typed), sanity-check that it reads like an accident description; if
  not, re-prompt for a proper explanation.
- Two further agents are explicitly in scope now: a per-company document RAG agent, and
  an agent that turns a client prompt into a proper DB search.

### Prior-decision note (on the record)

`ROADMAP.md` "Phase 2 - AI Services (removed)" records that an earlier AI stack
(`channel-gateway`, `doc-extractor`, `rag`, `langgraph-agent`, `guardrails`,
`ollama-assistant`) was built and deliberately removed; the project was pruned to three
services. This spec re-introduces an AI service tier and a Drive-files RAG - an explicit
user decision made with that history in view.

## Decisions

- **Service name:** `ai-service`. **Port:** `8001`. Guarded by `X-Internal-Token`.
- **Sole holder of LLM keys:** `OPENAI_API_KEY`, `GEMINI_API_KEY` (and
  `ANTHROPIC_API_KEY` available).
- **Sanity check:** lenient (reject only clearly-unrelated input); up to 2 re-prompts,
  then accept; model `gemini-2.5-flash-lite` + native structured output; fails open.
- **NL->DB agent:** Gemini **function-calling over Fleet API read endpoints** - no raw
  DB access; Fleet API keeps enforcing the permission matrix + tenant isolation.
- **RAG vector store:** **pgvector in Postgres, per-tenant** (schema-per-company).
- **RAG ingestion:** **automatic on Drive upload** (hook Fleet API's file-upload path).
- **Consumers:** Telegram bot and WebUI.
- **Agent framework:** hand-rolled with the `google-genai` SDK (function-calling /
  structured output). No LangGraph (consistent with the prior removal; YAGNI).
- **Migrated STT/vision keep their current model IDs** (`whisper-1`,
  `gemini-2.0-flash`) - relocation, not behavior change. A vision-model upgrade is a
  separate optional follow-up.
- **Observability:** **Phoenix (Arize), self-hosted**, instrumented via
  OpenTelemetry + OpenInference. Backend-agnostic by construction (OTel), so a later
  switch to Langfuse is possible without re-instrumenting call sites.

### OPEN DECISION (please confirm at review): who owns the pgvector tables?

Your invariant is "Fleet API is the sole Postgres writer." Two options:

- **(Recommended) Fleet API owns the vector tables** and exposes `store-chunks` and
  `search` as typed read/write tools; `ai-service` stays stateless w.r.t. Postgres and
  calls Fleet API for both. Pros: preserves the invariant; reuses Fleet API's existing
  schema-per-tenant resolution (`deps.py:81-95`). Cons: more inter-service plumbing; the
  index path is Fleet API -> ai-service -> Fleet API (made asynchronous to avoid a
  synchronous request cycle).
- **(Alternative) ai-service owns its own vector tables** as a scoped carve-out (AI
  artifacts are not domain data). Pros: no service cycle, RAG cohesive in one service.
  Cons: a second Postgres writer; must replicate schema-per-tenant scoping in ai-service.

This design assumes the recommended option. Flag it if you prefer the carve-out.

## Architecture

### New service: `services/ai-service/`

Scaffolded from `templates/python-service/`, following `services/fleet-api/`
conventions: FastAPI, `/health`, `X-Internal-Token` guard (`deps.verify_internal_token`),
config via `pydantic-settings` + `shepherd_config` overlay.

```
services/ai-service/app/
  main.py                 # FastAPI app + /health + routers
  config.py deps.py       # settings (keys, fleet_api_url) + verify_internal_token
  tracing.py              # NEW Phoenix/OTel setup: register + OpenInference instrumentors
  stt.py                  # Whisper impl, moved verbatim from bot
  vision.py               # Gemini doc-extract impl, moved verbatim from bot
  classify.py             # NEW Gemini classifier (gemini-2.5-flash-lite)
  fleet.py                # internal Fleet API client (X-Internal-Token + X-Caller-Context)
  db_agent.py             # NEW NL->DB function-calling agent + Fleet API tool catalog
  rag.py                  # NEW per-company RAG: ingest (extract/chunk/embed) + ask
  routers/{stt,vision,classify,agent,rag}.py
  tests/...
```

Shared request/response Pydantic models go in `libs/shepherd_contracts/ai.py`, imported
by `ai-service` and the bot client.

### Endpoints

| Method/Path | Input | Output | Phase |
|---|---|---|---|
| `GET /health` | - | `{status}` | 1 |
| `POST /stt/transcribe` | multipart audio + `language` | `{text}` | 1 |
| `POST /vision/extract` | multipart image + `doc_type`, `mime` | field dict | 1 |
| `POST /classify/accident-description` | `{text}` | `{is_accident: bool}` | 1 |
| `POST /agent/query` | `{question, caller_context}` | `{answer, used_tools[]}` | 2 |
| `POST /rag/index` | `{company_id, file_id, bytes|drive_link, metadata}` | `{chunks_indexed}` | 3 |
| `POST /rag/ask` | `{company_id, question, caller_context}` | `{answer, citations[]}` | 3 |

## Phase 1 - Consolidation + accident sanity check

### ai-service

- `stt.py` / `vision.py` moved verbatim (same model IDs).
- `classify.py`: lenient prompt; native structured output (`responseMimeType
  "application/json"` + `{is_accident: bool}` schema); **fails open** (returns `true`) on
  any provider/parse error, so an AI outage never blocks an accident report.

### Bot changes

- Delete `app/stt.py`, `app/vision.py`; add `app/ai.py` HTTP client (mirrors
  `app/fleet.py`): `transcribe()`, `extract()`, `is_accident_description()`. The client
  fails open for `is_accident_description` (returns `True`) when ai-service is
  unreachable.
- Repoint callers: `accident.py:87` (`stt`->`ai`), `doc_scan.py:126` and
  `update_driver.py:75` (`vision`->`ai`).
- `config.py`: drop `openai_api_key`/`gemini_api_key`; add `ai_service_url`.
- `pyproject.toml`: drop `openai` and `google-genai` (AI is now httpx-only).

### Accident sanity check (`accident.py` `accident_description`, lines 83-96)

1. Resolve `description` (voice -> `ai.transcribe`, else `ctx.text`) - unchanged.
2. `ai.is_accident_description(description)`.
3. **Pass** -> store, advance to `awaiting_road_clear`.
4. **Fail** -> read `ctx.state["desc_rejects"]` (default 0): if `< 2`, increment, stay in
   `awaiting_description`, send `texts.ACCIDENT_DESCRIPTION_RETRY`; if `>= 2`, accept and
   advance. (Up to 2 re-prompts, then accept.)

Router already re-fires the step on text/voice (`router.py:83-84`) - no router change.
New Hebrew string `texts.ACCIDENT_DESCRIPTION_RETRY` (what a proper description should
include: what happened, where, other vehicles involved).

## Phase 2 - NL->DB agent (function-calling over Fleet API)

- `POST /agent/query {question, caller_context}` -> `{answer, used_tools[]}`.
- `ai-service/app/fleet.py`: internal Fleet API client that forwards `X-Internal-Token`
  plus the caller's `X-Caller-Context` on every call, so **Fleet API enforces the
  caller's permissions and tenant scope** - the agent can never exceed them.
- `db_agent.py`: a curated tool catalog mapping Gemini function declarations to a subset
  of Fleet API read endpoints (v1: vehicles list/get, drivers list/get, accidents list,
  kpi, attendance summary). Loop: model selects a tool -> ai-service calls Fleet API with
  the caller context -> results returned to the model -> model emits a grounded NL
  answer. Bounded max tool-call iterations.
- Caller context originates at the surface (bot/webui) and is passed through; ai-service
  never elevates it.
- Consumers: bot (an "ask about my fleet" entry point) and webui (admin console query).
  Surface UX wiring is light in this spec; the contract is the endpoint.

## Phase 3 - Per-company RAG (Drive-files)

Assumes the recommended ownership option (Fleet API owns vector tables).

- **Schema:** new pgvector-backed model(s) in `shepherd-db` (per-company schema): chunk
  id, source file reference, chunk text, embedding vector, metadata. pgvector extension
  enabled in DB init (`db/`); table dimension matches the embedding model. Per the repo
  rule "no migrations until prod", this is added to models and the DB is rebuilt.
- **Fleet API gains** typed tools: `POST /rag/chunks` (persist chunks+embeddings for a
  company) and `POST /rag/search` (pgvector top-k similarity within the company schema).
- **Ingestion (automatic on upload):** Fleet API's file-upload path, after storing to
  Drive, triggers `ai-service POST /rag/index` **asynchronously** (background task, to
  avoid a synchronous service cycle). `ai-service` extracts text from the file (Gemini
  native PDF/image reading), chunks it, embeds chunks (Gemini embeddings, e.g.
  `gemini-embedding-001` - verify current ID), and persists them via Fleet API
  `POST /rag/chunks`.
- **Ask:** `POST /rag/ask {company_id, question, caller_context}` -> ai-service embeds the
  question, calls Fleet API `POST /rag/search` for top-k chunks in that company, then
  Gemini generates a grounded answer with citations. Company scoping is enforced
  end-to-end; never returns another company's chunks.
- Consumers: bot ("ask about our docs") and webui.

## Observability (Phoenix, self-hosted)

Because every LLM call funnels through `ai-service`, tracing is instrumented once there
and covers all capabilities (STT, vision, classifier, DB agent, RAG) automatically.

- **Mechanism:** OpenTelemetry + OpenInference auto-instrumentation of the provider
  SDKs - `openinference-instrumentation-openai` (Whisper) and
  `openinference-instrumentation-google-genai` (Gemini). Spans export over OTLP to a
  self-hosted Phoenix collector. No manual span code at call sites; new capabilities are
  traced for free as long as they go through the instrumented SDKs.
- **`app/tracing.py`:** calls `phoenix.otel.register(...)` and the two OpenInference
  instrumentors at app startup (from `main.py`), reading the collector endpoint from
  config. A single `tracing_enabled` flag (default off in tests) makes it a no-op when
  unset, so tests never export.
- **Usage slicing:** tag spans with `company_id` and `capability`
  (`stt`/`vision`/`classify`/`agent`/`rag`) so usage and token counts can be sliced per
  company and per feature in the Phoenix UI. Token usage and latency are captured per
  span by OpenInference; model pricing can be configured in Phoenix for cost rollups.
- **Privacy:** spans carry prompt/response payloads (company docs, accident text, driver
  data). Phoenix is self-hosted and internal-only - this data never leaves the
  environment. Not exposed publicly.
- **Deps (ai-service `pyproject.toml`):** `arize-phoenix-otel`,
  `openinference-instrumentation-openai`, `openinference-instrumentation-google-genai`
  (OTel SDK/exporter come transitively).

## Wiring

- `docker-compose.yml`: add a `phoenix` service (`arizephoenix/phoenix` image, UI/OTLP
  port `6006`, SQLite-backed volume for durability; Postgres backing via
  `PHOENIX_SQL_DATABASE_URL` is an option). Add `ai-service` (repo-root build context,
  port 8001, env
  `OPENAI_API_KEY`/`GEMINI_API_KEY`/`INTERNAL_SERVICE_TOKEN`/`FLEET_API_URL`/
  `PHOENIX_COLLECTOR_ENDPOINT`/`SHEPHERD_CONFIG`, `/health` healthcheck). `ai-service`
  `depends_on` `phoenix`. `telegram-bot` `depends_on` ai-service, loses the two LLM keys,
  gains `AI_SERVICE_URL`. `fleet-api` gains `AI_SERVICE_URL` (Phase 3 index trigger).
- `config.toml` + `config.example.toml`: add `ai_service_url` under `[services]`.
- `.env.example`: keys documented as owned by ai-service.

## Testing

- **ai-service** (provider SDKs + Fleet API stubbed):
  - Phase 1: `test_health`, `test_stt`, `test_vision`, `test_classify` (incl. fail-open).
  - Phase 2: `test_db_agent` - tool selection, caller-context forwarding, bounded loop,
    permission errors surfaced not bypassed.
  - Phase 3: `test_rag` - chunking/embedding (embeddings stubbed), company scoping on
    ask, citation assembly.
- **telegram-bot**: re-stub the `ai` HTTP client instead of `stt`/`vision`; update
  accident/doc_scan/update_driver tests; add sanity-check tests (pass->advance,
  fail->retry+counter, cap->accept, voice path, fail-open).
- **fleet-api** (Phase 3): `rag/chunks` + `rag/search` with company scoping under the
  existing testcontainers-postgres suite (pgvector enabled in the test image).
- **Tracing** is a no-op in all test runs (`tracing_enabled` off / no collector
  endpoint), so the suite never exports spans or requires a running Phoenix.

## Phasing (delivery order)

- **Phase 1** - consolidation + accident sanity check (smallest, ships the original ask).
- **Phase 2** - NL->DB function-calling agent.
- **Phase 3** - per-company RAG (pgvector + ingestion + retrieval; depends on the
  ownership decision and a pgvector-enabled DB image).

Each phase is independently shippable. The implementation plan sequences them.

## Docs to update (same commit as code, per repo pre-commit rule)

- `ROADMAP.md` - Phase 2: AI service re-introduced; Drive-files RAG now in build.
- root `README.md`, `services/telegram-bot/README.md`, new `services/ai-service/README.md`
  (document the Phoenix observability setup + how to open the UI).
- `.env.example`, `config.example.toml`.
- `CONTEXT.md` - if RAG/agent introduce canonical domain terms.

## Out of scope

- Upgrading the migrated vision model to `gemini-2.5-flash-lite` + structured output.
- Switching STT off Whisper (no evidence it improves Hebrew; needs an empirical A/B
  test first).
- A natural-language intent router that auto-picks between the DB agent and the RAG
  agent (v1 exposes them as distinct endpoints/entry points).

## Open questions

- Vector-table ownership (see "OPEN DECISION" above) - confirm before Phase 3.
- Exact current Gemini embedding model ID/dimension - verify on the API key before
  Phase 3.
