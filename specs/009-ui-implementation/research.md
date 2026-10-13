# Research and Open Decisions

## R-01: React + Vite with FastAPI on Vercel

**Decision:** Use a Vite-built React static frontend and a Python FastAPI backend in one repository; do not replace React with Next.js.  
**Context:** The requested stack is React/Vite and existing business code is Python.  
**Alternatives:** migrate to Next.js; host static files from FastAPI; separate Vercel projects.  
**Trade-offs:** Vite preserves requested tooling but requires polyglot routing; FastAPI static hosting reduces routing needs but loses independent static delivery; separate projects violate the one-URL goal.  
**Rationale:** preserves the requested frontend and existing backend.  
**Impact:** needs a Vercel composition configuration and same-origin API base.  
**Verification:** preview deploy loads / and POST/GET smoke checks reach /api/v1.

## R-02: One-project Vercel topology

**Decision:** Prefer Vercel Services with web at / and FastAPI at /api. Treat access as a deployment gate.  
**Context:** Official Vercel Services documentation says a frontend and FastAPI backend can share one project/domain, but Services is Private Beta as of the documentation reviewed on 2026-10-13.  
**Alternatives:** classic rewrites/functions; two Vercel projects; another host.  
**Trade-offs:** Services best fits independently built polyglot surfaces, but beta access is not guaranteed. Classic configuration must be verified against current project/runtime behavior.  
**Rationale:** it is the documented single-project arrangement and preserves modular-monolith boundaries.  
**Impact:** vercel.json uses Services only after beta access is confirmed; no microservice decomposition.  
**Verification:** project setting accepts Services config, preview routes /api/v1/health to FastAPI and /client routes to SPA.

## R-03: API routing and application composition

**Decision:** Preserve backend routes and mount public API under /api/v1; keep existing source routes only as documented compatibility routes until migrated.  
**Context:** source ingestion currently exposes /sources and /source-spans/resolve, while workflow routes use /api/v1. Review/evaluation have separate FastAPI app factories.  
**Alternatives:** browser calls multiple apps; proxy/duplicate business logic in frontend; silently rename routes.  
**Trade-offs:** a composition root is implementation work, but avoids incompatible route changes.  
**Rationale:** one FastAPI app is required and business logic remains in domain modules.  
**Impact:** Source v1 route normalization and saved-example endpoint are proposed contracts.  
**Verification:** composed app produces a unified OpenAPI document and all pre-existing pytest behavior passes.

## R-04: PostgreSQL in serverless deployment

**Decision:** Use managed persistent PostgreSQL and serverless-compatible connection handling; local SQLite remains local-only.  
**Context:** serverless instances are ephemeral and Vercel documents connection-exhaustion risks.  
**Alternatives:** deploy SQLite file; in-memory state; external data API; direct long-lived connections.  
**Trade-offs:** PostgreSQL needs migrations/configuration but preserves audit history; an HTTP data API reduces connection management but introduces vendor surface.  
**Rationale:** deployed revision/audit state must survive invocations.  
**Impact:** repository adapters and migrations are prerequisite work, not frontend behavior.  
**Verification:** cold-start/restart persistence test and concurrent revision conflict test against deployment database.

## R-05: Live LLM duration and async work

**Decision:** retain existing bounded synchronous terminal-run contracts for the PoC, with server timeout lower than configured function duration and idempotency keys.  
**Context:** Specs 004/006/007 define synchronous terminal responses; Vercel Functions return 504 at configured duration. Official limits vary by plan and Fluid Compute configuration.  
**Alternatives:** queues/background workers; streaming; new 202/polling contract.  
**Trade-offs:** synchronous UX is simplest but bounded; queues are explicitly excluded; streaming/polling need new contracts.  
**Rationale:** do not introduce infrastructure before demonstrated need.  
**Impact:** measure p95, set a conservative timeout/maxDuration, show failures explicitly.  
**Verification:** induced provider timeout yields typed non-success and approval remains blocked; deployment duration is recorded.

## R-06: OpenAPI client synchronization

**Decision:** consolidate only confirmed contracts plus x-integration-status annotations; generate client in CI and fail on uncommitted drift.  
**Context:** Specs have multiple OpenAPI files and some APIs are only domain services or separate apps.  
**Alternatives:** handwritten fetch models; use Pydantic types in frontend; invent endpoints.  
**Trade-offs:** consolidation requires maintenance but gives compile-time traceability.  
**Rationale:** contract-first constitution requirement.  
**Impact:** missing capabilities remain proposed until backend implementations exist.  
**Verification:** generation check plus contract examples in client tests.

## R-07: Evidence offsets and rendering

**Decision:** retain backend Unicode-code-point offsets and use server-returned spans only.  
**Context:** Spec 001 defines code-point, start-inclusive/end-exclusive semantics, while browser strings index UTF-16 units.  
**Alternatives:** browser substring indexes directly; normalize text; search quotations.  
**Trade-offs:** a conversion/display helper is needed, but it avoids corrupting non-BMP/combining character evidence.  
**Rationale:** source integrity overrides rendering convenience.  
**Impact:** helper is tested with diacritics, combining marks, CRLF, and astral characters.  
**Verification:** source excerpt and highlight match backend span-resolution fixtures exactly.

## R-08: revisions and stale responses

**Decision:** identity-gate query/mutation results by source version, note revision, and run ID; cancel superseded display requests.  
**Context:** asynchronous responses can arrive after an edit.  
**Alternatives:** last response wins; global mutable store.  
**Trade-offs:** more keys/guards, but prevents stale evidence presentation.  
**Rationale:** constitution and FR-42 require stale safety.  
**Verification:** Playwright race test edits during verification and confirms old response cannot replace revision n+1.

## R-09: synthetic, authentication-free demonstrations

**Decision:** no authentication is added; every UI surface labels synthetic-only and accepts only backend-attested synthetic records.  
**Context:** auth and real data are excluded.  
**Alternatives:** add demo accounts; accept arbitrary live clinical content.  
**Trade-offs:** no access control is appropriate only for the stated PoC boundary.  
**Rationale:** protects scope and constitution privacy constraints.  
**Verification:** forms/fixtures and API errors reject or warn on unsupported provenance; no auth requirement is represented as production readiness.

## R-10: cost, API failure, and retries

**Decision:** render backend cost/usage; frontend retries reads sparingly and commands only through idempotency-safe backend operations.  
**Context:** retries can duplicate external inference or decisions.  
**Alternatives:** unconditional React Query retry; client-side cost arithmetic.  
**Trade-offs:** some manual retry UX, but no false cost or duplicate action.  
**Rationale:** backend records authoritative inference cost and run state.  
**Verification:** retried idempotency key returns/replays same run; unavailable cost remains UNAVAILABLE.

## Official documentation reviewed

The Vercel Services, Services routing, Python runtime/FastAPI, Function Limits, Fluid Compute, Environment Variables, and connection-pooling documentation were reviewed on 2026-10-13. Important volatile facts are deployment gates: Services beta access, plan-specific duration, runtime support, and database provider configuration must be checked again immediately before implementation/deployment.

