# Deployment Contract

## Required topology

One Vercel project/deployment URL serves:

- React/Vite static web application at /, including SPA fallback.
- One composed FastAPI application for /api/v1/*.

Preferred configuration uses Vercel Services with a root web service and /api FastAPI service. Vercel Services is documented as Private Beta; access confirmation is a mandatory pre-deployment condition. The exact current configuration syntax must be validated with current official Vercel documentation and vercel build before production use.

## Build and runtime requirements

- Frontend: Node version pinned by implementation; npm ci; Vite production build; output directory defined by Vite.
- Backend: Python version pinned in pyproject.toml/.python-version; uv/pip production dependency install; FastAPI exports one ASGI app from the composition root.
- Contract generation runs before frontend type check/build and fails on drift.
- Backend bundle excludes virtual environments, local SQLite data, caches, fixtures not required for runtime, and secrets.

## Routing

Public routing preserves /api/v1/{path} for FastAPI. More-specific API routing precedes SPA catch-all. The backend receives the original /api/v1 path and mounts routes accordingly. Existing non-v1 source routes require an explicit compatibility decision; the frontend should use the canonical v1 façade once implemented.

## Environment variables

| Variable class | Examples | Exposure |
| --- | --- | --- |
| Server secret | DATABASE_URL, LLM_API_KEY/provider credential | Vercel Secret/sensitive variable; Python only |
| Server configuration | LLM_MODEL, PROVIDER_TIMEOUT_SECONDS, RETRY_LIMIT, APP_ENV | Python only |
| Public build configuration | VITE_API_BASE_URL=/api | Browser-safe only |

Secrets are never VITE_ prefixed, committed, emitted to logs, returned by health checks, or embedded in client source maps. Production and preview use distinct database/configuration scopes. Rotate credentials through Vercel environment configuration and redeploy.

## Persistence and health

PostgreSQL is required for deployed immutable sources, notes, runs, decisions, and audit history. Configure serverless-safe pooling/connection strategy, migration procedure, backups/retention policy, and one-region placement compatible with database latency. Health response checks process and database readiness only; it must omit content, credentials, connection strings, prompts, and model responses.

## Timeout/failure handling

Set FastAPI/provider timeout below the selected Vercel Function/service maxDuration with cleanup/persistence margin. Use existing backend bounded retries and idempotency. Function 504, provider timeout, malformed output, database unavailability, and persistence error map to typed safe errors/non-success runs; approval remains unavailable. No queue, background worker, or polling is introduced by this feature.

## Deployment verification

1. vercel build succeeds from repository root.
2. Preview root loads the frontend and deep route fallback works.
3. GET /api/v1/health is safe and ready.
4. A synthetic-only source → note → review-context smoke test succeeds.
5. A forced timeout/dependency failure displays failure and blocks approval.
6. A new source/revision/audit event remains after a fresh invocation.
7. Browser bundle inspection confirms no credential/config secret.

## Rollback

Use a prior Vercel deployment only when database migration compatibility is confirmed. Migrations must be forward compatible until a rollback window expires; otherwise deployment rollback is blocked and a compatible forward fix is required. Record deployment ID, application revision, schema version, and verification result in release notes.

