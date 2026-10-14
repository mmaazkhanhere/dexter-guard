# Technical Plan: React Frontend Integration and One-URL Vercel Deployment

## Architecture

Retain one Python FastAPI application with domain-separated modules from Specs 001–008 and add a React/TypeScript Vite frontend. This is a modular monolith, not a microservice system. The browser calls same-origin API routes only. A composition-root task must combine the currently separate source-ingestion, human-review, and evaluation app factories/routers into one configured FastAPI application before production deployment.

Proposed repository shape after implementation:

- frontend/: Vite React app, generated API client, UI tests.
- backend/src/app/: FastAPI composition root and dependencies.
- backend/src/{source_ingestion,nursing_notes,claim_extraction,evidence_verification,deterministic_validation,source_coverage,human_review,evaluation}/: existing domain modules retained.
- api/: minimal Vercel Python entrypoint importing the composition root.

## Frontend structure

React Router routes: /documentation, /verification/:noteId, /review/:noteId, and /evaluation. Shared shell has desktop nav, current source/revision badge, error region, and synthetic-data warning.

Feature modules own presentation only:

- documentation: transcript form, saved-example picker, note generation/import, facts panel, draft editor.
- verification: source/note panes, claim list, finding filters, evidence details, span highlighter.
- review: decision forms, suggestions, re-verification actions, approval/rejection card, audit timeline.
- evaluation: run picker, metric cards/table, comparison, failure/case inspector.
- api: generated OpenAPI client, adapter layer, typed error normalization, idempotency-key helper.
- state: React Query hooks, revision-identity guards, local draft state.
- ui: shadcn/ui primitives and accessible common components.

The shared notification region announces terminal action outcomes through accessible status and alert semantics. Success messages identify the affected source, note, revision, verification, decision, or disposition and state any required next step. Failure messages include the normalized stable error code and explicitly state which persisted state was not changed. Notifications supplement, rather than replace, persistent inline error and eligibility states.

Use Tailwind CSS and shadcn/ui for consistent controls. Use React Hook Form with Zod for only browser-owned input validation; backend Pydantic validation remains authoritative. Use TanStack Query for server state, not duplicated domain stores.

## Component boundaries and state

Each workspace has a route-level query keyed by immutable identity. Suggested keys include source/sourceId/sourceVersion, review/noteId/revision, audit/noteId, verification/verificationRunId, and evaluation/evaluationRunId. Mutation completion invalidates the exact note context, suggestions, audit, and related run keys. It never blindly overwrites a newer selected revision.

Local draft state contains text, base revision, dirty flag, and last server revision. A mutation records a request token plus source ID/version and note ID/revision. Apply its response only if all identities still match the active target. Save/accept-correction success adopts the returned successor then clears the previous draft; 409 conflict keeps user text, refreshes server state, and asks the reviewer to reconcile manually.

## API integration

Generate a TypeScript client from contracts/openapi.yaml during CI and build. Wrap generated operations in feature hooks that:

1. add correlation/idempotency values for commands,
2. decode typed ApiError envelopes and unexpected transport failures,
3. expose mutation status and retryability,
4. validate response identity before cache writes,
5. invalidate/refetch review context after mutations.

The consolidated contract includes existing routes and explicitly marks missing capabilities as proposed backend dependencies. No frontend facade shall parse prose to replace a missing backend operation.

## Evidence display

The renderer uses server-returned source and note offsets. It verifies ranges are in bounds before displaying a mark; it never computes evidence from matching strings. Invalid spans show an evidence-unavailable message. Overlaps are represented by a selected-finding overlay plus non-color labels; the focused finding controls scroll and contextual excerpt. Claim spans are note-revision specific; source spans are source-version specific.

## Correction, verification, and approval lifecycle

Manual edit and accepted correction invoke revision creation with expected revision. The UI immediately treats predecessor results as stale, then refetches backend context. Claim re-verification is visually scoped as feedback. Full-note verification is the only UI action that can refresh eligibility. The eligibility card consumes server state, shows component/run failure details, and only enables approval when server eligibility is affirmative. Approval/rejection and decisions remain backend transactions.

## Accessibility and layout

Target desktop from 1024px; optimize review at 1280px with resizable/persisted local panes where practical. At narrower widths, stack panes without declaring mobile support. Meet WCAG 2.2 AA intent: semantic headings/landmarks, visible focus, keyboard row selection, ARIA live regions for async changes, status text/icons in addition to color, adequate contrast, labels/errors tied to fields, and no auto-scroll that steals focus.

## Test strategy

- Vitest + React Testing Library: forms, typed error mapping, revision guards, span safety, status labels, decision requirements, metric state display.
- MSW/client contract tests: generated types and request/response examples including 409, 422, 503, timeout, malformed response.
- Playwright: four workspace journeys, stale mutation race, failure cannot approve, evidence-invalid no highlight, history, saved-vs-live labels.
- Existing pytest: preserve all Specs 001–008 unit/integration suites.
- API contract tests: composed FastAPI OpenAPI must conform to the consolidated contract; proposed endpoints remain failing discovery tests until implemented.

## Deployment plan

Preferred topology is one Vercel project using Vercel Services: a Vite static web service at / and a FastAPI service mounted at /api, with public /api/v1/* routing to Python and the frontend as the catch-all. Both share a deployment URL. Vercel documents Services as Private Beta, so implementation must verify project access before selecting it.

Fallback decision gate: if Services access is unavailable, evaluate and prove a single-project static Vite output plus Python Function routing configuration on the current Vercel plan. If that cannot deploy both surfaces under one URL, deployment is blocked; do not silently split into multiple projects because FR-48 requires one URL.

Use persistent PostgreSQL for deployed data behind existing repositories. SQLite is local-only and the checked-in data/nursing_notes.sqlite3 is not deployed state. Python dependencies/pinned Python version and frontend dependencies have separate lockfiles. Configure a server-side max duration consistent with Vercel plan limits and the backend LLM timeout; leave margin for error mapping/persistence. Current synchronous backend contracts have no 202/polling interface, so do not add a queue: bound calls with server timeout/retry/idempotency. If measured work exceeds the selected limit, create a separately versioned asynchronous contract rather than pretending completion.

## Environment and operations

Server-only variables include DATABASE_URL, LLM provider credentials, model/provider configuration, timeout/retry settings, and deployment environment identifier. VITE_API_BASE_URL may be a public same-origin value only; no VITE_ prefixed secret is permitted. Health checks verify process health and database reachability without transcript/note content or secrets. Structured logs contain IDs, status, latency, cost/tokens, and error codes only.

Deploy previews against isolated synthetic-only data/configuration. Production uses a separately configured PostgreSQL database and secret scope. Roll back by promoting a prior compatible deployment only after confirming schema compatibility; migrations must be forward-compatible or have an approved rollback plan.

## Constitution check

Evidence fidelity: preserves immutable source/note identities and server evidence spans. Human authority: no client auto-approval/auto-fix and backend enforces eligibility. Spec/contract first: generated client comes from versioned contract; missing contracts are explicit. Modular/deterministic: presentation does not duplicate domain logic. Evaluation: dashboard displays backend metrics/provenance. Privacy: synthetic-only and no secrets/client content telemetry. Failure discipline: typed non-success states fail closed. All principles must be rechecked at implementation PR review.

