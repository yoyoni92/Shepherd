# Impl: Feature 4 - Nav Consolidation

**Status**: done
**Epic**: `plans/epics/multi-tenancy-and-company-admin.md` (Feature 4)
**Mode**: ponytail (full) + TDD
**Depends on**: none hard; reuse F2's `NavItem` (allowedRoles + children)

## Goal

Fewer top-level tabs: nest maintenance-types under Vehicles, nest accidents under
Events, and remove the Chat/Assistant tab entirely.

## Ponytail guardrails (provisional)

- Reuse F2's `NavItem.children`; don't invent a second nav mechanism.
- "Nest" = move the existing page's content into a tab/section of the parent page,
  reusing the existing component. No rewrite of the maintenance-types/accidents UI.
- Chat removal = delete the nav entry + route; leave agent/assistant services alone
  (separate epic).

## TDD slices (to refine at start)

Webui (`services/webui`, Vitest + Playwright smoke):
- [x] sidebar no longer lists maintenance-types / accidents / chat as top-level.
- [x] Vehicles page renders the maintenance-types section; Events page renders accidents.
- [x] navigating to `/chat` is gone (route removed) - no dead link.

## Verify command

`cd services/webui && npm test` (+ `npm run e2e` smoke).

## Running log / decisions

- 2026-06-26: Implemented (ponytail + TDD). Moved `NAV`/`NavItem` from
  `Sidebar.tsx` into `lib/nav.ts` so the top-level structure is unit-testable;
  `tests/nav.test.ts` now asserts maintenance-types/accidents/chat are not
  top-level and vehicles/events remain. Nested via in-page shadcn `Tabs` (not
  sidebar `children`, kept on the type) - extracted `MaintenanceTypesPanel` and
  `AccidentsPanel` from the route bodies (no UI rewrite) and reused them in both
  the Vehicles/Events tab strips and the now-thin standalone route pages. Kept
  `/maintenance-types` and `/accidents` routes reachable (minimal call - no
  redirect/middleware churn; they just no longer have a sidebar entry). Chat was
  already routeless; removed the remaining dead refs (`ChatSurface.tsx`, Topbar
  title map entries, the `useAssistant.ts` eslint override, smoke-test `chat`
  section). Verified: typecheck + lint clean, 25 vitest files green (coverage
  93%, above 85% gate), `next build` clean (19 routes).
