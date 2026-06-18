# Shepherd

AI-powered vehicle fleet management. Conversational AI agent: **Moshes**.

Design & build plans: [`../plans/`](../plans/README.md) (design) and
[`../plans/implementation/`](../plans/implementation/00-overview.md) (TDD build plans).

## Layout

```
libs/             shared contracts (pydantic models + provider interfaces)
db/               Postgres schema, migrations, seed           [T1-T5 done]
services/         fleet-api [done], channel-gateway [done], doc-extractor [done],
                  image-analyser [done], rag [done], langgraph-agent [done],
                  guardrails, webui                            [planned]
n8n/              workflow JSON + Code-node units              [planned]
infra/            docker-compose, env                          [planned]
```

## Dev setup

- Python **3.12** (services), managed with **Poetry**. WebUI: Next.js + **pnpm**.
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
