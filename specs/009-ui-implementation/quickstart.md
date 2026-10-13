# Quickstart (Spec 009 implementation)

## Current implementation status

The composed backend entrypoint is `backend/src/app/main.py`; the Vercel wrapper is
`backend/main.py`; backend tests are under `backend/tests/`; and the browser
application is under `frontend/`. The local
backend commands below were verified on 2026-10-13. Frontend dependency
installation and Vercel preview deployment remain environment-dependent gates.

## Local commands

From the repository root:

```powershell
uv sync --group dev
uv run pytest
uv run uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The browser-safe setting is `VITE_API_BASE_URL=/api/v1`. Database URLs and LLM
credentials are server-only variables; never prefix them with `VITE_` or commit
them. Use the examples in `backend/.env.example` and
`frontend/.env.example` as the variable-name reference.

Frontend validation, once dependencies are available:

```powershell
cd frontend
npm run api:generate
npm test -- --run
npm run lint
npm run check
npm run test:e2e
```

The Playwright command is a browser-only end-to-end gate. It starts the local
Vite and FastAPI services and requires the Playwright Chromium test browser;
Chromium is not bundled into the application or production deployment.

Deployment configuration is in `vercel.json`. The supported topology is Vercel
Services with `/api/*` routed to FastAPI and all other paths routed to Vite;
the project must be set to the Services framework. Before production, provision
PostgreSQL, configure server-only secrets, and run `vercel build` plus the
preview smoke checks in `docs/deployment/spec-009-vercel-decision.md`.


