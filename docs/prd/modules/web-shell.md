# Module: web-shell (`frontend/` scaffolding + `frontend/src/shared/` + `App.tsx`)

**Skills:** frontend, typescript, ui-design · **Read also:** `04-ui-spec.md` (esp. §5 final visual decisions), visual reference `demo/`; `04` §1 and §4, `01-architecture.md`

## Job
The frame everything sits in, so `map` and `panel` can be built in parallel: the Vite app, the **UTD-style layout**
(top bar, 400px left panel, map area), shared state, the typed API client, live events, design tokens and UI primitives.

## Owns
`frontend/{package.json,vite.config.ts,index.html,tailwind.config.ts,tsconfig*.json}`, `frontend/src/main.tsx`,
`frontend/src/App.tsx`, `frontend/src/shared/**`.

## Provides
```ts
// src/shared/
api-types.ts      // generated: `npm run gen:api` (openapi-typescript http://localhost:8000/openapi.json)
api.ts            // typed wrappers for every route in 02-contracts §4
queries.ts        // TanStack hooks: useScenarios, useDemoState, useOverlays(hour), useBuildings, useUtilities, useImpact(hour),
                  // useImpactFor(id), useSummary, usePlans(filter), useFixFirst, useWorkOrders, useResources, useReferrals,
                  // useReports, useMessages(partyId), useMessagingStatus
                  // + mutations: loadScenario, setHour, approvePlan, rejectPlan, updateWorkOrder, generateReport, simulateMessage, reset
useEvents.ts      // single EventSource('/api/events'); event → invalidate:
                  // timeline.changed|scenario.loaded → demoState, overlays, impact, summary, plans, fixFirst, resources, utilities
                  // impact.updated → impact, summary · plans.updated|plan.changed → plans, fixFirst, summary
                  // workorder.changed → workOrders, plans · message.* → messages · resources.changed|referral.changed → resources, referrals
                  // report.created → reports. Also keeps the last 100 events for an optional activity feed
ui-store.ts       // tiny Zustand (or React context) store: selectedBuildingId, panelView ('overview'|'buildings'|'building'|
                  // 'fixfirst'|'workorders'|'help'|'reports'|'messages'), layer toggles {hazard, buildings, power, workorders, help, messages}
format.ts         // money(cents) → "$1.65M"/"$980k", hours(h) → "−12h"/"+2d", riskColor(level), phaseColor(phase)
tokens.css        // colors per 04 §4 (risk scale, phase colors, accent teal, slate top bar), light theme only
ui/               // shadcn: button, badge, card, tabs, tooltip, dialog, scroll-area, separator, toggle, dropdown-menu, progress
```

## Layout (`App.tsx`)
`<TopBar/>` (owned here: scenario dropdown → `loadScenario`, buttons that set `panelView`, live net exposure / $ avoided from
`useSummary`, reset in the overflow menu) + `<aside 400px>{<Panel/>}</aside>` + `<main>{<MapView/>}</main>`.
`Panel` is the default export of `src/modules/panel/index.tsx` and `MapView` of `src/modules/map/index.tsx`.
Ship placeholder components so the app runs before those modules land. Vite proxies `/api` → `:8000`. One route `/` is enough.

## Acceptance
- `npm run dev` shows the full layout with placeholders. The scenario dropdown lists 3 scenarios from the API and switching works.
- `useEvents` reconnects after a backend restart. Invalidation visibly refreshes data.
- `npm run build` passes.
