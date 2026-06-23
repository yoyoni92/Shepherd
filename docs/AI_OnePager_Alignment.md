# Shepherd - OnePager Tech-Stack Alignment (Current vs Desired)

Compares the **code as it stands** against the tech stack promised in
`docs/FleetManagement_OnePager.md`. Scope: **tech-stack usage**, not feature
parity. Source of truth for "Current" is `services/`.

**Legend:** ✅ aligned · 🟡 partial / divergent (works, but not the stack the
one-pager names) · ❌ missing (promised, not present/wired)

---

## 0. Scorecard

| Layer | Element | OnePager (desired) | Current (code) | Status |
|------|---------|--------------------|----------------|--------|
| **1 Interfaces** | Admin Web UI framework | Gradio / Streamlit | Next.js (React/TS) | 🟡 |
| | KPI dashboard | yes | webui `/dashboard` + fleet-api `/kpi` | ✅ |
| | RAG action chat | yes | webui `/chat` → langgraph agent (rag+fleet tools) | ✅ |
| | Ollama-grounded assistant | yes | webui `/assistant` → ollama-assistant → ollama `llama3` | ✅ |
| | Telegram bot + phone auth | yes | n8n flows + channel-gateway, `channel_identities` | ✅ |
| **2 n8n pipeline** | Webhook intake | yes | n8n Telegram webhook | ✅ |
| | **Guardrails input** in flow | yes | service exists, **not called by n8n** | ❌ |
| | **Doc-type classifier** in flow | yes (image-analyser) | service exists, **not called by n8n** | ❌ |
| | **Information Extractor (Bedrock)** in flow | yes | service exists; n8n only **uploads to S3**, never extracts | ❌ |
| | **AI Agent** in flow | yes | langgraph exists, **not called by n8n** | ❌ |
| | LLM Chain (record update / summary) | yes | partial: subs write to fleet-api directly | 🟡 |
| | **Guardrails output** in flow | yes | service exists, **not called by n8n** | ❌ |
| | Router / team routing | yes | n8n router + 13 sub-workflows | ✅ |
| **3 EC2 services** | RAG: LangChain | yes | `langchain` / `langchain_anthropic` | ✅ |
| | RAG: ChromaDB | yes | `chromadb` (Ephemeral - not persisted) | 🟡 |
| | RAG: generation engine | **Llama.cpp** | **Anthropic Claude** at runtime (Llama.cpp only in `eval --live`) | 🟡 |
| | RAG: embeddings | (implied local) | `sentence-transformers` multilingual MiniLM | ✅ |
| | Image Analyser: PyTorch CNN | ResNet-50 / EfficientNet-B0 | ResNet-50 transfer-learn, 5-class | ✅ |
| | Image Analyser: ≥200 imgs, >75% acc | yes | synthetic generator + eval harness; **no committed checkpoint** | 🟡 |
| | Image Analyser: Dockerized + deployed | yes (25% rubric) | **no Dockerfile, not in compose** | ❌ |
| | Guardrails engine | **NeMo Guardrails** | **guardrails-ai** + deterministic pre-checks | 🟡 |
| | Guardrails input rail (auth/topic/lang) | yes | deterministic auth + langdetect + RestrictToTopic + ToxicLanguage | ✅ |
| | Guardrails output rail (no false claims) | yes | ProvenanceV1 grounding | ✅ |
| | LangGraph Agent | yes | implemented + wired to webui | ✅ |
| **4 LLM APIs** | Bedrock Claude (PDF→context) | yes | doc-extractor bedrock (default provider) | ✅ |
| | Agent reasoning LLM | **Gemini / GPT-4o** | **Anthropic Claude** (`claude-sonnet-4-6`); Gemini only as extractor fallback | 🟡 |
| | RAG generation LLM | **Llama.cpp** | Anthropic Claude (see above) | 🟡 |
| | Ollama local chat | yes | ollama `llama3` | ✅ |
| **Prompt Eng (25%)** | 5 surfaces × 5 iters | yes | extractor, agent, rag, guardrails, ollama logs all present | ✅ |

---

## 1. The missing dots (no decision needed - just build)

These are unambiguous gaps where the service exists but isn't connected, or a
promised artifact is absent. Closing them does **not** change any technology
choice.

### G1. Wire the AI pipeline into n8n  ❌ (biggest gap)
Today n8n calls only `fleet-api`, Telegram, and S3. The one-pager's Layer-2 chain
`Guardrails-in → classifier → extractor → agent → Guardrails-out` is absent. The
license/insurance docs are uploaded to S3 by the bot but never sent for
extraction or classification.

Add HTTP Request nodes in the intake flow:
- `POST {guardrails}/check/input` after the webhook (gate on `pass`).
- `POST {image-analyser}/analyse` with the S3 key → branch on `doc_type`.
- `POST {doc-extractor}/extract` for license/insurance docs.
- `POST {langgraph-agent}/agent/run` for free-text action requests.
- `POST {guardrails}/check/output` before replying to the user.

Requires adding these service URLs to the n8n container env in `docker-compose.yml`.

### G2. Dockerize image-analyser + add to compose  ❌
No `Dockerfile`, not in `docker-compose.yml`. For the EC2-services rubric (25%) it
must deploy like the others. Add a `Dockerfile` (mirror doc-extractor's) and a
compose service on port 8007 with `S3_BUCKET`, `IMAGE_CONFIDENCE_MIN`, AWS creds.

### G3. Train + commit the image model  🟡
`artifacts/` has only a stale `accuracy.txt` / `confusion_matrix.npy`, no
`model.pth`. Without it `/analyse` runs an **untrained** head (random output).
Run `generate → train → eval`, confirm >75%, and commit/ship `model.pth`.

### G4. (Optional) Persist ChromaDB  🟡
RAG uses an **Ephemeral** Chroma client - the index is empty on every restart and
must be re-synced. Fine for a demo if `sync.bulk` runs on startup; otherwise
switch to a `PersistentClient` with a volume.

---

## 2. The divergences (a decision is needed)

Here the code uses a **different, generally newer** technology than the one-pager.
"Full alignment to the one-pager" would mean changing working code. In most of
these the current choice is an upgrade, so the cheaper/safer fix is to **update
the one-pager** instead. Each row needs a call: **match the one-pager** (change
code) or **update the one-pager** (change the doc).

| # | One-pager says | Code does | Recommendation |
|---|----------------|-----------|----------------|
| D1 | RAG generation via **Llama.cpp** | Anthropic Claude (Llama.cpp survives in `eval --live`) | **Update one-pager** - Claude is higher quality and already wired; Llama.cpp stays as the offline/local fallback. |
| D2 | Agent reasoning via **Gemini / GPT-4o** | Anthropic Claude `claude-sonnet-4-6` | **Update one-pager** - consistent Claude stack; or add a provider switch if a non-Anthropic agent is a hard requirement. |
| D3 | Guardrails via **NeMo Guardrails** | guardrails-ai + deterministic rails | **Judgment call** - functionally equivalent (input auth/topic/lang + output grounding). Swapping to NeMo is real work for no capability gain; recommend updating the one-pager unless NeMo is graded by name. |
| D4 | Web UI via **Gradio / Streamlit** | Next.js | **Update one-pager** - Next.js is a superset of the requirement (KPIs + RAG chat + Ollama assistant all present). |

> Note: the rubric table in the one-pager grades *capabilities* (KPIs, RAG chat,
> guardrail rails, etc.), not library names - so D1-D4 likely don't affect the
> grade. Confirm before spending effort matching names.

---

## 3. Recommended path to "all dots connected"

1. **Build the pure gaps** (G1-G3): wire n8n pipeline, dockerize + deploy
   image-analyser, train + commit the model. (G4 optional.)
2. **Decide D1-D4.** Default recommendation: keep the code, update the one-pager
   so its stack matches reality - except D3 (NeMo), which is the only one worth a
   second look if guardrail *library* is graded.
3. After decisions, sync `docs/FleetManagement_OnePager.md` and the affected
   `plans/*.md` in the same change.

See `docs/AI_SETUP_AND_TESTING.md` for the provisioning + manual test of each
service referenced above.
</content>
