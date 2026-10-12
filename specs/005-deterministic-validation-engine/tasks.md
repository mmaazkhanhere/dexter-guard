# Spec 005 — Implementation Tasks

**Execution prerequisite:** A reviewer must first complete [checklist.md](checklist.md). Task checkboxes represent implementation progress and are intentionally all open.  
**Dependencies:** Specs 001–003 contracts; Spec 004 alignment contract when semantic alignment is supplied.

## Phase 0 — Repository and contract baseline

- [ ] T001 Map the existing Python/FastAPI/Pydantic/SQLite modules, repositories, migrations, router, dependency injection, and pytest conventions; record the mapping in `compatibility-review.md`. **Requirements:** FR-16. **Depends on:** none.
- [ ] T002 Verify upstream Spec 001 source snapshot and span contracts, Spec 002 note revisions, Spec 003 claims, and Spec 004 alignment output. Refuse to implement adapter assumptions not supported by their contracts. **Requirements:** DVE-001, DVE-009. **Depends on:** T001.
- [ ] T003 Review and approve ADR 004 with the component owners; revise its status if alternatives or downstream contracts differ. **Requirements:** DVE-001, DVE-012. **Depends on:** T002.
- [ ] T004 Implement versioned Pydantic domain contracts and OpenAPI request/response mapping from `data-model.md` and `contracts/`; enforce requested note binding, stable IDs, ruleset versions, conditional finding fields, complete ValidationRun metadata, and typed API errors. **Requirements:** DVE-010, DVE-011, DVE-013–DVE-015. **Depends on:** T001, T002.
- [ ] T005 Write contract tests for requested note binding; reusable fact/claim IDs across distinct preselected alignments; `ALIGN-001` rule-ID closure; nullable persisted claim revision; typed scalar/BP shapes; resolved-record category rejection; complete run metadata; conditional finding fields; and 404/409/422/500/503 error envelopes. **Requirements:** DVE-001, DVE-003, DVE-010, DVE-011, DVE-013–DVE-015. **Depends on:** T004.

## Phase 1 — Pure deterministic primitives (test first)

- [ ] T006 Write failing unit/property tests for German comma/dot decimal parsing, exact decimal serialization, `ml↔L` and `mg↔g`, and disallowed conversions. **Requirements:** DVE-002, DVE-004. **Depends on:** T004.
- [ ] T007 Implement pure `Decimal` parser and `UnitNormalizer`, including the v1 category/unit matrix; never use binary floats, tolerance, clinical ranges, or prose inference. **Requirements:** DVE-002, DVE-004, DVE-006. **Depends on:** T006.
- [ ] T008 Write and implement typed measurement validation for scalar categories and two-component `mmHg` blood pressure; return `STR-001`/`STR-003` without attempting dependent numeric rules. **Requirements:** DVE-003, DVE-007. **Depends on:** T007.
- [ ] T009 Write unit tests and implement `NUM-001`, `NUM-002` trace behavior, `NUM-003`, `NUM-004`, and `NUM-005`; test equal equivalents, mismatches, incompatible dimensions, structured approximation states, and changed BP components. **Requirements:** FR-11, DVE-005–DVE-008. **Depends on:** T008.
- [ ] T010 Write and implement Unicode code-point evidence validation for source/version equality, range boundaries, and exact source substring quotation. **Requirements:** DVE-009. **Depends on:** T004.
- [ ] T011 Add evidence tests for umlauts, combining characters, emoji/non-BMP text, empty/reversed/out-of-range spans, outdated versions, and altered quotation. **Requirements:** EVD-001–EVD-003. **Depends on:** T010.

## Phase 2 — Rule orchestration and persistence

- [ ] T012 Implement preselected-pair validation: each alignment resolves one known source fact and claim with matching category; duplicate pair IDs/internally inconsistent references fail safely; repeated fact/claim IDs across different pairs remain valid; and `UNAVAILABLE`/`AMBIGUOUS`/`REJECTED` yield `ALIGN-001` `NOT_EVALUABLE`. **Requirements:** DVE-001. **Depends on:** T002, T009.
- [ ] T013 Implement deterministic orchestration and ordering: independent evidence checks; structural-before-numeric precedence; input alignment then catalog ordering; no pass findings by default. **Requirements:** DVE-009–DVE-012. **Depends on:** T009, T011, T012.
- [ ] T014 Add regression tests proving malformed or unaligned input never creates a numeric contradiction; rule results contain complete traceability and do not call/import model clients or network code. **Requirements:** FR-16, DVE-001, DVE-011. **Depends on:** T013.
- [ ] T015 Create immutable `ValidationRun` persistence and repository integration using project conventions; store exact source and requested note revision binding, ruleset/contract/engine versions, input digest, ordered results, and optional idempotency binding. **Requirements:** DVE-011–DVE-013. **Depends on:** T001, T013.
- [ ] T016 Write repository integration tests for immutable source resolution, stale version rejection, missing records, wrong-note provenance conflict, nullable persisted claim revision yielding `STR-002`, unavailable storage, append behavior, input digest stability, and repeatable output. **Requirements:** DVE-009, DVE-011, DVE-014, DVE-015. **Depends on:** T015.

## Phase 3 — API and acceptance fixtures

- [ ] T017 Implement the FastAPI endpoint and dependency injection using the published OpenAPI contract; return no full transcript, no approval state, and no LLM dependency. **Requirements:** FR-16. **Depends on:** T015.
- [ ] T018 Write API integration tests for complete successful run metadata; conditional finding fields; `SCHEMA_ERROR`; 404 missing references; 409 wrong-note provenance; 503 dependency failure; 500 unexpected failure; source/evidence failures; and minimized evidence exposure. **Requirements:** DVE-009–DVE-015. **Depends on:** T017.
- [ ] T019 Create versioned synthetic German fixture manifest for AT-001 through AT-021, including repeated preselected pairs, note binding, stable evidence-reference IDs, `ALIGN-001` outcome coverage, resolved-record category-rejection coverage, and exact expected rule/API-error outcomes. **Requirements:** FR-11, FR-16. **Depends on:** T014.
- [ ] T020 Implement acceptance tests over fixtures. Assert exact finding rule ID, outcome, reason, conditional source fact/claim/alignment/evidence-reference IDs, expected/observed/unit nullability, `requires_review`, complete run metadata, API error code/status, and no valid-equivalence warning. **Requirements:** all acceptance scenarios. **Depends on:** T018, T019.
- [ ] T021 Add property/repeatability tests that process the same immutable inputs multiple times and assert identical canonical JSON output and ordering. **Requirements:** AT-012, DVE-011. **Depends on:** T020.

## Phase 4 — Consumer handoff and completion

- [ ] T022 Provide a Spec 007 consumer fixture/documentation showing the finding fields, rule-version display, `NOT_EVALUABLE` treatment, and separation from final severity/approval policy. **Requirements:** DVE-011, DVE-012. **Depends on:** T020.
- [ ] T023 Export Spec 008 fixture/rule manifest with rule/ruleset versions and expected outcomes; do not add evaluation thresholds to online validation. **Requirements:** FR-16. **Depends on:** T019.
- [ ] T024 Add structured, minimized telemetry for run identity, ruleset/engine versions, outcome counts, rule IDs, latency, and safe failure reasons; assert no full transcript is logged. **Requirements:** FR-16. **Depends on:** T017.
- [ ] T025 Run format, static, unit, contract, integration, acceptance, and `git diff --check` commands configured by the repository; record exact results. **Requirements:** definition of done. **Depends on:** T021–T024.
- [ ] T026 Have a human reviewer update the reviewer-owned requirements checklist; implementation must not update it. **Depends on:** T025.
- [ ] T027 Run [converge.md](converge.md), append only newly discovered gap tasks, implement them, and repeat until convergence reports `Converged`. **Depends on:** T026.

## Dependency summary

```text
T001 → T002 → T003/T004 → T005/T006
T006 → T007 → T008 → T009
T004 → T010 → T011
T002 + T009 → T012 → T013 → T014 → T019
T001 + T013 → T015 → T016/T017 → T018
T018 + T019 → T020 → T021 → T025 → T026 → T027
T020 → T022; T019 → T023; T017 → T024
```
