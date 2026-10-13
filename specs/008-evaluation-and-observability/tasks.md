# Spec 008 Implementation Tasks

**Execution gate:** [checklist.md](checklist.md) is reviewer-owned. Do not implement while any checklist item remains unchecked without explicit user/reviewer direction. A task checkbox represents implementation completion only; it never substitutes for the independent checklist review.

**Dependencies:** Approved Spec 008 requirements; actual verified interfaces of Specs 001â€“007; Python/FastAPI/Pydantic/SQLite conventions. [P] indicates independent work after listed dependencies.

## Phase 0 â€” Compatibility and benchmark foundation

- [x] T001 Inspect and record actual application wiring, repository/migration conventions, ports/routes, timeout/retry/idempotency behavior, and frontend host in compatibility-review.md. **Requirements:** all. **Done when:** assumptions in plan are confirmed or gaps are explicitly recorded; no source code changes.
- [x] T002 Verify upstream identity/version fields and result contracts from Specs 001â€“007 for source/note/claim/finding/coverage/review handoff. **Depends on:** T001. **Requirements:** FR-26, FR-29â€“33. **Done when:** a reference-only adapter matrix proves no duplicated reliability logic.
- [x] T003 [P] Write the synthetic benchmark annotation guide, schema manifest, and category/family/split authoring policy. **Depends on:** T002. **Requirements:** FR-26, FR-27. **Done when:** every required annotation and held-out rule is authorable/reviewable.
- [x] T004 [P] Create and independently review an initial 100+ scenario synthetic German benchmark with one or more fixed candidates where required. **Depends on:** T003. **Requirements:** FR-26, FR-27. **Done when:** scenarios cover EVAL-001â€“005 and EVAL-010â€“013; no real data appears. Optional resident-context fixtures are excluded unless their upstream contract is verified.
- [x] T005 Implement dataset validators for schema, hashes, IDs, source/note spans, annotations, category coverage, duplicates, family integrity, split protection, and synthetic-only markers. **Depends on:** T003â€“T004. **Requirements:** FR-26, FR-27, EVAL-010, EVAL-011, EVAL-013. **Tests:** deterministic unit/fixture tests.

## Phase 1 â€” Contracts, domain model, persistence

- [ ] T006 Implement Pydantic evaluation domain models/status unions from data-model.md and OpenAPI contract validation, including explicit case-result, configuration, finding-match, comparison, and tagged metric schemas. **Depends on:** T001â€“T002. **Requirements:** FR-29, FR-30, FR-32, FR-33. **Tests:** model/contract tests.
- [ ] T007 Implement append-only SQLite evaluation repository and migration/init convention for datasets, runs, case results, findings, matches, metrics, comparisons, and exports. **Depends on:** T006. **Requirements:** FR-30, FR-32, FR-33. **Tests:** persistence, restart, immutability, idempotency tests.
- [ ] T008 [P] Implement content-minimised evaluation telemetry/configuration capture, including code/config/model/prompt/rule/price/tokens/cost states. **Depends on:** T006. **Requirements:** FR-30. **Tests:** assert no source/note/prompt/raw-output content in logs.

## Phase 2 â€” Pure scoring and aggregate measures

- [ ] T009 Implement EVALUATION_MATCHING-v1: target/status/type/attribute/evidence matching, deterministic tie breaks, duplicate suppression, partial/misclassification outcomes, and no double-counting. **Depends on:** T006. **Requirements:** FR-29. **Tests:** EVAL-001â€“005 plus permutation/property-style tests.
- [ ] T010 Implement metric calculators for every specified metric, raw-count outputs, zero denominators, failure/unscorable accounting, Wilson intervals, and latency/cost summaries. **Depends on:** T009. **Requirements:** FR-29. **Tests:** EVAL-003, EVAL-005â€“007, boundary/percentile tests.
- [ ] T011 Implement paired baseline/validated comparator with candidate/source/task hash checks and separate observed/simulated review results. **Depends on:** T006, T010. **Requirements:** FR-28, FR-29. **Tests:** EVAL-008, EVAL-009, EVAL-015.
- [ ] T012 Implement regression comparison/disposition that preserves raw deltas, uncertainty, reference compatibility, and visible REVIEW_REQUIRED for unapproved thresholds. **Depends on:** T010â€“T011. **Requirements:** FR-31. **Tests:** EVAL-014.

## Phase 3 â€” Runner and pipeline integration

- [ ] T013 Implement reference-only adapters to actual Spec 003â€“006 pipeline ports, mapping outputs to ObservedFinding without recomputation. **Depends on:** T002, T006. **Requirements:** FR-29â€“31. **Tests:** fake-port contracts first, then verified integration tests.
- [ ] T014 Implement the headless evaluation runner: explicit dataset/split selection, preflight validation, fixed candidates, pipeline execution, stage capture, matching, metrics, immutable persistence, JSON result, and human summary. **Depends on:** T005, T007â€“T013. **Requirements:** FR-26â€“33. **Tests:** EVAL-001â€“015 without React; demo tracking uses immutable upstream references only.
- [ ] T015 Implement timeout, unavailable provider, malformed output, invalid evidence, interruption, persistence-failure, and retry/idempotency handling. **Depends on:** T014. **Requirements:** FR-29, FR-31. **Tests:** EVAL-007, EVAL-010 and failure-injection integration tests.
- [ ] T016 [P] Add deterministic mocked-provider/saved-fixture CLI or Python entrypoint and CI invocation; add separately marked live benchmark and upstream-reference synthetic-demo tracking invocations. **Depends on:** T014â€“T015. **Requirements:** FR-31, FR-33. **Tests:** repeatability, no-frontend, demo-reference, and no-duplicate-ingestion tests.

## Phase 4 â€” Results, examples, and diagnostics

- [ ] T017 Implement evaluation-run query/export API from contracts/evaluation.openapi.yaml, historical retrieval, and stable error handling. **Depends on:** T007, T014. **Requirements:** FR-32, FR-33. **Tests:** API/export/authorization-free synthetic fixtures.
- [ ] T018 Implement the lightweight report/dashboard or existing-client route: run selector, provenance, metric raw counts, pairs, category/failure analysis, missed critical cases, drill-down, latency/cost, and export. **Depends on:** T017. **Requirements:** FR-32. **Tests:** component/API contract and accessibility text-label tests.
- [ ] T019 Implement saved-example registration and live-execution labeling, ensuring historical records cannot be shown as fresh inference. **Depends on:** T014, T017. **Requirements:** FR-33. **Tests:** EVAL-012.

## Phase 5 â€” Acceptance, regression, and handoff

- [ ] T020 Add deterministic acceptance suite for EVAL-001 through EVAL-015, all global evidence-integrity invariants, FR-26â€“33 traceability, and 100+ benchmark validation. **Depends on:** T005â€“T019. **Requirements:** all. **Done when:** every core acceptance scenario has executable evidence; optional extensions are separately labelled.
- [ ] T021 Add protected held-out reference-run/regression workflow and report fixtures; ensure only critical-error recall uses the approved >=95% gate and other changes are TBD/review-required. **Depends on:** T012, T016, T020. **Requirements:** FR-27, FR-31.
- [ ] T022 Run formatter, static/compile, unit, contract, repository, integration, headless acceptance, and report tests; record commands/results in convergence evidence. **Depends on:** T020â€“T021. **Requirements:** all.
- [ ] T023 Update analyze.md, run converge.md, append any verified gap tasks, and obtain independent checklist re-review. **Depends on:** T022. **Requirements:** all.

## Requirement traceability

| Requirement | Primary tasks | Acceptance evidence |
| --- | --- | --- |
| FR-26 | T003â€“T005, T014, T020 | EVAL-001â€“005, EVAL-010, EVAL-013 |
| FR-27 | T003â€“T005, T021 | EVAL-011 |
| FR-28 | T011, T014, T018 | EVAL-008, EVAL-009, EVAL-015 |
| FR-29 | T009â€“T011, T014â€“T015 | EVAL-001â€“007 |
| FR-30 | T006â€“T008, T014 | configuration/provenance contract tests |
| FR-31 | T012, T015â€“T016, T021 | EVAL-007, EVAL-014 |
| FR-32 | T017â€“T018 | drill-down/export report tests |
| FR-33 | T014, T016, T019 | EVAL-012 |

