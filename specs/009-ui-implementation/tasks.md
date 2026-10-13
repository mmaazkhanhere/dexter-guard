# Implementation Tasks

Tasks are ordered by dependency and vertical slices. [P] means independently parallelizable once prerequisites are complete.

## Phase 0 — contract and deployment discovery

- [ ] T001 Verify and compose existing FastAPI routers into one app; identify concrete dependency wiring and preserve route compatibility. FR-47, FR-48. Prerequisite: none. Files: src/app/, tests/api/. Completion: unified OpenAPI can serve all confirmed endpoints. Test: pytest composition/route smoke.
- [ ] T002 Confirm Vercel Services access, plan duration/memory limits, supported Python runtime, and PostgreSQL provider/connection mode. FR-48, FR-49. Prerequisite: none. Files: deployment decision record/vercel.json. Completion: preview topology decision is evidenced. Test: vercel build/preview smoke.
- [ ] T003 [P] Reconcile the consolidated contract with Specs 001–008 and mark all unavailable endpoints proposed. FR-47. Prerequisite: none. Files: contracts/*. Completion: no implementation fact is invented. Test: OpenAPI lint and traceability review.

## Phase 1 — foundations

- [ ] T004 Create frontend Vite/React/TypeScript/Tailwind/shadcn scaffold and desktop app shell. FR-34. Prerequisite: T001. Files: frontend/src/app, frontend/package.json. Completion: four routes/rendering shell compile. Tests: Vitest route/a11y smoke.
- [ ] T005 [P] Add OpenAPI generation, typed client wrapper, ApiError normalization, idempotency helper, and MSW fixtures. FR-47, FR-49. Prerequisite: T003. Files: frontend/src/api. Completion: generated client has no handwritten duplicate DTOs. Tests: generation drift + unit error tests.
- [ ] T006 [P] Implement revision-aware React Query keys, mutation guards, and local unsaved draft state. FR-42, FR-47. Prerequisite: T005. Files: frontend/src/state. Completion: stale response cannot alter newer identity. Tests: race-condition unit test.

## Phase 2 — Documentation vertical slice

- [ ] T007 Build transcript entry and saved-example selection; wire source submission/retrieval. FR-35. Prerequisite: T005; saved examples requires proposed contract implementation. Files: frontend/src/features/documentation. Completion: source identity/rendered errors work. Tests: RTL valid/invalid/example flow.
- [ ] T008 Build generation/import, structured facts, and editable draft panel. FR-36, FR-37. Prerequisite: T007. Files: documentation components/hooks. Completion: origin/facts/source reference are preserved. Tests: RTL provider failure/import distinction.
- [ ] T009 Implement missing saved-example and source-route normalization adapters only in backend composition layer if discovery confirms absence. FR-35, FR-46. Prerequisite: T001/T003. Files: src/app/api. Completion: documented contract passes without duplicating domain logic. Tests: pytest contract tests.

## Phase 3 — Evidence vertical slice

- [ ] T010 Implement claim/finding list and source/note side-by-side evidence viewer. FR-38, FR-39. Prerequisite: T005/T006 and review-context availability. Files: frontend/src/features/verification. Completion: all status/provenance categories are visible. Tests: RTL status and unavailable-evidence cases.
- [ ] T011 Implement Unicode-safe span projection, focus/scroll behavior, overlapping highlights, and non-color severity/rule labels. FR-39. Prerequisite: T010. Files: frontend/src/features/verification/spans. Completion: invalid spans never highlight. Tests: Unicode/combining/astral unit tests and Playwright selection flow.
- [ ] T012 Add verification trigger and terminal failure states. FR-38, FR-42, FR-49. Prerequisite: T010. Files: verification hooks/panels. Completion: failed/timed-out response cannot appear verified. Tests: MSW timeout/malformed response tests.

## Phase 4 — Human review vertical slice

- [ ] T013 Implement finding decision/adjudication forms and suggestion presentation/explicit acceptance. FR-40, FR-41. Prerequisite: T005/T006. Files: frontend/src/features/review. Completion: required rationales and unusable suggestions are enforced in UI. Tests: RTL decision/suggestion tests.
- [ ] T014 Implement immutable manual save, stale indicator, claim/full-note re-verification lifecycle. FR-40, FR-42. Prerequisite: T013. Files: review editor/hooks. Completion: successor revision updates identity; stale conflict preserves draft. Tests: Playwright edit-during-run race.
- [ ] T015 Implement backend-driven approval/rejection eligibility card and commands. FR-43, FR-49. Prerequisite: T014. Files: review approval components. Completion: no local path approves on failed/stale/critical state. Tests: Playwright direct-409 failure and rejection-after-failure.
- [ ] T016 [P] Implement audit/revision timeline and historical read-only view. FR-44. Prerequisite: T005. Files: frontend/src/features/review/audit. Completion: events/revisions remain ordered and non-mutating. Tests: RTL timeline/audit contract tests.

## Phase 5 — Evaluation

- [ ] T017 Implement evaluation run picker, saved/live provenance labels, metric cards/table, denominator/reason display. FR-45, FR-46. Prerequisite: T005 and evaluation endpoints. Files: frontend/src/features/evaluation. Completion: UI never recalculates metrics. Tests: RTL metric state tests.
- [ ] T018 Implement baseline/validated comparison and case/failure inspector. FR-45. Prerequisite: T017. Files: evaluation detail components. Completion: case-level traceability is navigable. Tests: Playwright saved/live/failure workflow.

## Phase 6 — integration, deployment, and acceptance

- [ ] T019 [P] Add accessibility, responsive desktop, error-boundary, and telemetry-content tests. FR-34, FR-49. Prerequisite: T004–T18 relevant components. Completion: no color-only status; safe errors. Tests: axe/RTL/Playwright.
- [ ] T020 Configure PostgreSQL migration/repository deployment adapters and health endpoint. FR-48, FR-49. Prerequisite: T001/T002. Files: src/app, migration/deployment config. Completion: restart-safe audit/revision storage. Tests: deployed integration persistence.
- [ ] T021 Configure Vercel Services, API routing, env validation, build scripts, and rollback runbook. FR-48. Prerequisite: T002/T004/T020. Files: vercel.json, api entrypoint, docs. Completion: preview has one URL for SPA/API. Tests: vercel build and smoke suite.
- [ ] T022 Execute API contract, pytest, Vitest, Playwright, deployed smoke, and cross-document traceability review. FR-34–FR-49. Prerequisite: all above. Completion: evidence/approval/failure acceptance cases pass or documented blockers remain. Tests: full CI matrix.

