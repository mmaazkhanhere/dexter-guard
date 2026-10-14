# AGENTS.md

## Project overview

Dexter Guard is a synthetic German nursing-documentation reliability engine. It
combines a Python/FastAPI backend with a React/Vite frontend and exposes the
application through Vercel Services. The system is evidence-oriented: source
transcripts are authoritative, immutable, and referenced by exact source spans.

The repository is governed by [.specify/memory/constitution.md](.specify/memory/constitution.md).
Read it before making changes to validation, evidence, review, evaluation,
model integration, persistence, or user-facing approval behavior.

## Repository map

- `backend/src/app/`: FastAPI composition, routing, and application wiring.
- `backend/src/source_ingestion/`: source documents, versions, repositories,
  validation, and source-span resolution.
- `backend/src/nursing_notes/`, `claim_extraction/`,
  `evidence_verification/`, `deterministic_validation/`, `source_coverage/`,
  `human_review/`, and `evaluation/`: downstream domain boundaries.
- `backend/tests/`: Python unit, contract, service, repository, and API tests.
- `frontend/src/`: React application, typed API client, state, shared UI, and
  feature pages.
- `frontend/tests/`: Vitest/component tests; `frontend/tests/e2e/` contains
  Playwright tests.
- `specs/`: feature specifications, plans, tasks, contracts, fixtures, and
  evaluation material. These are the implementation source of truth for feature
  behavior.
- `docs/`: architecture, ADRs, operations, deployment, and evaluation notes.
- `data/evaluation/`: versioned synthetic evaluation assets.
- `vercel.json`: the supported Vercel topology: `/api/*` to FastAPI and other
  paths to the Vite application.

## Local setup

Prerequisites: Python 3.11+, `uv`, Node.js/npm, and Playwright Chromium when
running browser end-to-end tests.

From the repository root:

```powershell
uv sync --group dev
uv run pytest
```

Install frontend dependencies separately:

```powershell
cd frontend
npm ci
```

Use `backend/.env.example` and `frontend/.env.example` as the environment
variable references. `VITE_API_BASE_URL` is browser-safe and normally points to
`/api/v1`. Database URLs, LLM keys, and other server-only values must never be
prefixed with `VITE_` or committed to the repository.

## Common commands

Backend, from the repository root:

```powershell
uv run pytest
uv run uvicorn app.main:app --env-file backend/.env --reload --port 8000
```

Frontend, from `frontend/`:

```powershell
npm run dev
npm test
npm run lint
npm run check
npm run test:e2e
npm run api:generate
```

`npm run api:generate` regenerates `frontend/src/api/generated.ts` from
`specs/009-ui-implementation/contracts/openapi.yaml`; run it when the API
contract changes. The Playwright gate starts the local Vite and FastAPI services
and requires the Playwright browser installation.

## Engineering rules

- Follow the sequence `constitution -> feature spec -> plan -> tasks -> tests ->
  implementation -> evaluation -> review` for feature work.
- Do not implement an ambiguous safety, evidence, contract, or approval behavior
  by guessing. Resolve it in the relevant specification first.
- Keep source transcripts immutable within a validation run. Revisions create a
  new version; they must not overwrite historical text.
- Treat `(source_id, source_version)` as the source identity. A `SourceSpan`
  uses zero-based, inclusive `start` and exclusive `end` offsets and must be
  checked against the exact stored version.
- Preserve provenance on every evidence-bearing artifact. Do not copy an
  excerpt as an untraceable authority or create alternate source identifiers.
- Keep deterministic validation, persistence, identifiers, versioning, numeric
  rules, and span resolution independent of LLMs and network access.
- Use Pydantic/OpenAPI contracts at component and API boundaries. Keep stable
  machine-readable error codes and preserve structured failure outcomes.
- Keep transport, domain logic, repositories, model adapters, and presentation
  behind narrow interfaces. Do not put business rules in HTTP handlers or React
  components when they belong in a domain boundary.
- The system is a pre-approval quality gate, not an autonomous clinical
  decision-maker. Only an explicitly authorized human may approve or reject a
  draft; critical verification failures must remain blocking.
- Use synthetic data only. Never add real patient data to code, fixtures, logs,
  screenshots, model requests, or demos. Do not expose secrets in telemetry.
- For frontend changes, preserve typed API usage and accessible review flows;
  warning state must not rely on color alone.
- Add or update an ADR when a design decision crosses component boundaries.

## Change workflow

Before editing, locate the applicable feature under `specs/` and read its
`spec.md`, `plan.md`, `tasks.md`, contracts, and relevant fixture/evaluation
files. For cross-cutting changes also read `docs/architecture.md` and the
constitution.

When changing behavior:

1. Update the normative specification and stable requirement/contract IDs when
   the scope or behavior changes.
2. Add deterministic unit, contract, API, or scenario tests before or alongside
   the implementation.
3. Keep changes limited to the specified slice; do not silently relax review
   policy, alter evidence semantics, or introduce unapproved features.
4. Update traceability, fixtures, evaluation manifests, and documentation when
   they are affected.
5. Run the narrowest relevant checks first, then the complete applicable gates.

Generated API types should be regenerated from the OpenAPI contract rather than
hand-edited. Treat migrations and versioned evaluation fixtures as intentional
artifacts: review their compatibility and provenance before changing them.

## Verification expectations

At minimum, backend changes should pass `uv run pytest`. Frontend changes
should pass `npm test`, `npm run lint`, and `npm run check` from `frontend/`;
changes affecting routing, documentation workflows, or full user journeys
should also run `npm run test:e2e`.

For changes involving evidence, review, model adapters, or evaluation, verify
the relevant failure paths as well as success cases: invalid or missing spans,
version mismatches, unsupported input, malformed model output, unavailable
providers, unresolved contradictions, and edit/revalidation transitions.

Before deployment-related changes, review
`docs/deployment/spec-009-vercel-decision.md` and run the documented preview
smoke checks. Production deployment requires server-only secrets and
PostgreSQL configuration; local tests must remain runnable without an LLM
provider or external network.
