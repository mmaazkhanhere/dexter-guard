# Quickstart (Specification Target)

This repository currently has Python modules under src/ and no frontend directory, package.json, composed FastAPI entrypoint, PostgreSQL adapter, Vercel configuration, or frontend test suite. Commands marked **planned** depend on this feature's future implementation and are not assertions that they work today.

## Verified current backend commands

From the repository root:

1. Install the existing Python project: uv sync --group dev
2. Run existing backend tests: uv run pytest
3. Existing source-ingestion ASGI entrypoint: uv run uvicorn source_ingestion.main:app --reload

The current source-ingestion app exposes source and note routes and optional adapters; it is not yet the complete composed production app.

## Planned local development commands

1. Install frontend dependencies: cd frontend; npm ci
2. Create local environment files from documented examples; never commit secrets.
3. Set server-only DATABASE_URL, LLM credentials, provider/model configuration, timeout/retry configuration, and synthetic-only environment flag.
4. Set VITE_API_BASE_URL=/api for the browser. Do not place LLM or database credentials in VITE_ variables.
5. Initialize synthetic test data with the planned backend seed command or versioned evaluation fixture loader (exact command: TBD by implementation).
6. Start composed backend: uv run uvicorn app.main:app --reload --port 8000
7. Start frontend: cd frontend; npm run dev
8. Open the URL printed by Vite and exercise Documentation.

## Planned validation commands

- Frontend unit tests: cd frontend; npm run test
- Frontend type/lint check: cd frontend; npm run check
- Backend tests: uv run pytest
- API contract generation/check: planned script, likely frontend npm run api:generate -- --check
- End-to-end tests: cd frontend; npm run test:e2e
- Production frontend build: cd frontend; npm run build
- Local full topology validation: vercel dev -L, after Vercel Services eligibility/configuration is confirmed.

## Planned Vercel deployment

1. Confirm Vercel Services private-beta access and selected plan duration limits.
2. Provision PostgreSQL and apply audited migrations; do not use the repository SQLite file as deployment state.
3. Configure production and preview secrets in Vercel project settings (DATABASE_URL and LLM credentials) and non-secret configuration separately.
4. Link the repository-root Vercel project and validate configuration: vercel link; vercel build.
5. Deploy preview: vercel deploy. Deploy production only after preview smoke tests: vercel deploy --prod.
6. Verify the returned one deployment URL: root page loads; /api/v1/health returns safe health; a synthetic source submission succeeds; review-context/audit requests preserve IDs; a forced timeout remains non-eligible.

If Services is unavailable, stop at the topology gate in research.md and prove the approved fallback before deploying. Do not create two projects to work around the one-URL requirement.

