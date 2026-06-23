# Shepherd - Roadmap

## Done

### Phase 1 - Foundation
- `libs/` shared Pydantic contracts and provider interfaces
- `db/` Postgres schema, migrations 0001-0009, seed data
- `services/fleet-api` - REST API, SQLAlchemy ORM, 85 tests

### Phase 2 - AI Services
- `services/channel-gateway` - Telegram + webapp inbound, S3 media, n8n forwarding
- `services/doc-extractor` - Bedrock + Gemini vision extractors, reconcile-by-plate
- `services/rag` - multilingual embeddings, Chroma vector index, LangChain/Claude generator
- `services/langgraph-agent` - LangGraph planner -> tool-exec -> synthesiser, Fleet API + RAG tools
- `services/guardrails` - auth + language pre-checks, topic + grounding rails

### Phase 3 - UX + Operations
- `services/webui` - Next.js 15 admin console (dashboard, Fleet Chat, Upload, Review Queue, Bot Management)
- `services/n8n` - invite-only Hebrew Telegram bot, 84-node workflow, driver + admin flows

---

## Up Next

### Observability - Langfuse

**What**: Integrate [Langfuse](https://langfuse.com) as the LLM observability layer across all AI services.

**Why**: The project has four independent AI surfaces (rag, langgraph-agent, guardrails, doc-extractor) each logging prompts locally (V1-V5 prompt logs). Langfuse replaces ad-hoc logging with a unified trace/span model, eval scores, and a cost dashboard - all without changing inference code.

**Scope**:

| Service | What to instrument |
|---------|--------------------|
| `langgraph-agent` | Trace per `/agent/run` call; spans for planner, each tool, synthesiser |
| `rag` | Span per `/query`; log retrieved chunks + rerank scores as observations |
| `guardrails` | Spans for input-check + output-check; score pass/fail + detected language |
| `doc-extractor` | Span per extraction; log provider (Bedrock/Gemini), plate, confidence |

**Approach**:
1. Add `langfuse` to each affected service's `pyproject.toml`.
2. Use `langfuse.decorators.observe` on the function boundaries above - zero boilerplate.
3. Pass `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` via `.env` (self-hosted or cloud).
4. Add Langfuse container to `docker-compose.yml` for local dev (Postgres backend already present).
5. Wire evals: thumbs-up/down from WebUI Fleet Chat -> `langfuse.score()`.

**Outcome**: single pane of glass for latency, cost, prompt regressions, and user satisfaction scores across all AI surfaces.

---

### Evals - Automated Regression Suite

Run the existing `eval/` harness on every CI push against a golden fixture set; gate merges on pass rate >= 95%.

### Image Analyser

`services/image-analyser` skeleton exists. Wire it into the accident flow in n8n as a vision step after photo upload.

### RAG - Incremental Index Updates

Currently the Chroma index is rebuilt from scratch. Add a diff-based update triggered by Fleet API vehicle-profile change events.

### WhatsApp Channel

Channel-gateway has a WhatsApp seam (stub). Implement the provider and wire Twilio/WhatsApp Business credentials.
