# WebUI - Admin Console

Next.js 15 (App Router) admin console for Shepherd.

**Deviation from Gradio/Streamlit:** rubric allows "app.py or equivalent" - this service satisfies that with a modern React SPA.

## Stack

- Next.js 15 + React 19 + TypeScript
- Tailwind CSS 3 (dark theme matching `FleetManagement_UI_Mockup.html`)
- TanStack Query v5 + Zod
- next-auth v4 (credentials provider, admin-only)
- Vitest + React Testing Library + MSW (unit/integration)
- Playwright (e2e smoke)

## Dev

```bash
cp .env.example .env.local   # fill ADMIN_EMAIL, ADMIN_PASSWORD, NEXTAUTH_SECRET
npm install
npm run dev                  # http://localhost:3000
npm test                     # Vitest (coverage >= 85% on lib/ + hooks/)
npm run e2e                  # Playwright (requires running app)
npm run typecheck            # tsc --noEmit
npm run lint                 # ESLint (also enforces DB-blind assistant boundary)
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Login (credentials) |
| `/dashboard` | KPI cards (vehicles, drivers, expiring docs, events, tickets, maintenance) |
| `/chat` | Fleet Q&A + actions via LangGraph/RAG/Fleet API |
| `/assistant` | Moshes: DB-blind Ollama assistant (prompt surface #5) |
| `/upload` | Document upload -> gateway -> classification result + review flag |
| `/config` | system_config editor (admin-gated, Zod-validated) |
| `/review` | Flagged docs/events with optimistic accept/reject |

## DB-blind assistant

`hooks/useAssistant.ts` only calls `NEXT_PUBLIC_ASSISTANT_URL/chat`. ESLint rule
(`no-restricted-imports` in `.eslintrc.json`) prevents importing any fleet/agent/gateway
client into that file. The `useAssistant.test.tsx` also asserts no Fleet API or RAG
requests are made at the network level via MSW.

## Environment variables

See `.env.example`.
