# Implementation Tasks

Tasks are ordered by dependency and vertical slices. Checked tasks have implementation and local evidence; unchecked tasks are externally blocked or still missing acceptance evidence.

## Phase 0 - contract and deployment discovery

- [x] T001 Compose the existing FastAPI routers into one app and preserve route compatibility. Evidence: `backend/src/app/main.py`, `backend/tests/api/test_composition.py`.
- [ ] T002 Confirm Vercel Services access, plan limits, supported Python runtime, and PostgreSQL provider. Partial repository topology exists in `vercel.json`, but account access, plan limits, PostgreSQL credentials, and preview smoke remain external blockers.
- [x] T003 Reconcile the consolidated contract with Specs 001-008 and label unavailable endpoints proposed. Evidence: generated OpenAPI contract and `backend/tests/api/test_spec_009_contract.py`.

## Phase 1 - foundations

- [x] T004 Create the Vite/React/TypeScript desktop shell with four routes. Evidence: `frontend/src/app/`, `frontend/src/components/layout/`, `frontend/tests/app-shell.test.tsx`, `npm run check`.
- [x] T005 Add OpenAPI generation, typed client wrapper, error normalization, idempotency helper, and generated schema aliases. Evidence: `frontend/src/api/`, `frontend/src/api/generated.ts`, `frontend/package-lock.json`, `npm run api:generate`, `npm run lint`.
- [x] T006 Implement revision-aware React Query keys, mutation guards, and local unsaved draft state. Evidence: `frontend/src/state/workspace.tsx`, `frontend/tests/workspace.test.ts`, `frontend/src/features/review/ReviewWorkspace.tsx`.

## Phase 2 - Documentation vertical slice

- [x] T007 Build transcript entry, saved-example selection, and source submission/retrieval. Evidence: `frontend/src/features/documentation/DocumentationPage.tsx`, `frontend/tests/documentation-workflow.test.tsx`, backend composition tests.
- [x] T008 Build generation/import, structured facts, and editable candidate panel. Evidence: documentation workspace and external-import test; generation remains backend-provider controlled and fails closed when unavailable.
- [x] T009 Implement saved-example and source-route normalization adapters in the composition layer. Evidence: `backend/src/app/main.py`, composition and contract route tests.

## Phase 3 - Evidence vertical slice

- [x] T010 Implement the side-by-side transcript/note/finding evidence viewer and backend status display. Evidence: `frontend/src/features/verification/VerificationPage.tsx`.
- [x] T011 Implement Unicode-safe source spans, overlap handling, focus/scroll behavior, and non-color labels. Evidence: `frontend/src/features/verification/spans.ts`, `frontend/tests/spans.test.ts`, verification workspace focus behavior. Browser E2E evidence remains part of T022.
- [x] T012 Add verification triggering and terminal failure handling. Evidence: review workspace full-verification mutation, backend-controlled status/error rendering, and approval guard.

## Phase 4 - Human review vertical slice

- [x] T013 Implement finding decisions and explicit suggestion acceptance/rejection. Evidence: `frontend/src/features/review/ReviewWorkspace.tsx`, typed decision hook, backend review contract.
- [x] T014 Implement immutable saves, stale indicators, revision identity updates, and re-verification lifecycle. Evidence: review workspace and revision guard tests.
- [x] T015 Implement backend-driven approval/rejection eligibility and commands. Evidence: approval button requires backend `approvalEligible` and current valid verification; rejection requires a reason.
- [x] T016 Implement persisted audit/revision history display. Evidence: `useAudit`, review audit panel, backend `/reviews/{note_id}/audit` route.

## Phase 5 - Evaluation

- [x] T017 Implement evaluation run picker, provenance labels, backend metric cards, denominators, and unavailable states. Evidence: `frontend/src/features/evaluation/EvaluationWorkspace.tsx`, composed evaluation router, frontend build/tests.
- [x] T018 Implement baseline/validated comparison and case/failure inspection. Evidence: evaluation workspace comparison and immutable case-result inspector.

## Phase 6 - integration, deployment, and acceptance

- [x] T019 Add an application error boundary, responsive desktop layout, accessible text labels, and safe-error tests. Evidence: `frontend/src/components/shared/ErrorBoundary.tsx`, `frontend/tests/error-boundary.test.tsx`, `npm run lint`, Vitest.
- [x] T023 Add accessible terminal-action notifications for source/example, note, review, verification, decision, and disposition workflows. Evidence: `frontend/src/components/shared/Toaster.tsx`, action handlers, and frontend notification tests.
- [x] T024 Consolidate Documentation and Evidence Verification into one Generate & Verify workspace with automatic source persistence, full-note verification, read-only result inspection, and Human Review handoff. Evidence: `frontend/src/features/documentation/DocumentationPage.tsx`, `frontend/src/features/verification/VerificationPage.tsx`, navigation tests, and documentation workflow tests.
- [x] T025 Preserve source transcript/resident state across the Documentation and Human Review route boundary and add compact evidence-linked verification findings. Evidence: `frontend/src/state/workspace.tsx`, `frontend/src/features/documentation/DocumentationVerificationWorkspace.tsx`, `frontend/src/features/verification/VerificationPage.tsx`, and frontend regression tests.
- [ ] T020 Configure PostgreSQL migrations/repository adapters and restart-safe deployed persistence. Blocked: no PostgreSQL provider/credentials or migration framework is available; local SQLite/in-memory repositories are not claimed as deployed persistence.
- [ ] T021 Complete Vercel preview configuration and smoke verification. Repository configuration and build scripts exist in `vercel.json`, but Vercel account access, preview build, one-URL smoke, and production secrets remain unavailable.
- [ ] T022 Execute the complete API-contract, backend, frontend, Playwright, deployed-smoke, and traceability matrix. Backend and frontend unit/build gates pass; Playwright/deployed/PostgreSQL gates remain open.

