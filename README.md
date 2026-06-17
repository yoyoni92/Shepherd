# Shepherd

AI-powered vehicle fleet management. Conversational AI agent: **Moshes**.

Design & build plans: [`../plans/`](../plans/README.md) (design) and
[`../plans/implementation/`](../plans/implementation/00-overview.md) (TDD build plans).

## Layout

```
libs/             shared contracts (pydantic models + provider interfaces)
db/               Postgres schema, migrations, seed           [T1-T5 done]
services/         fleet-api, channel-gateway, doc-extractor,
                  image-analyser, rag, langgraph-agent,
                  guardrails, webui                            [planned]
n8n/              workflow JSON + Code-node units              [planned]
infra/            docker-compose, env                          [planned]
```

## Dev setup

- Python **3.12** (services), managed with **Poetry**. WebUI: Next.js + **pnpm**.
- Per package: `poetry env use python3.12 && poetry install && poetry run pytest`.

## Status

Phase 1 (foundation) in progress - starting with `libs/` shared contracts (TDD).
