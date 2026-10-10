# Tasks: Nursing Note Generation

**Prerequisite:** The reviewer must complete `checklist.md` before implementation begins. Tasks remain planning artifacts until that gate passes.

## Phase 1 — Foundation

- [ ] T001 Read `.specify.memory/constitution.md`, map its principles to this feature, and amend `plan.md` for any project-specific constraint before code changes.
- [ ] T002 Inspect existing API, persistence, test, and LLM-adapter conventions; replace illustrative stack choices in `plan.md` only where required for consistency.
- [ ] T003 Add strict runtime schemas for drafts, facts, provenance, generation output, and both API requests/responses.
- [ ] T004 Add persistence migrations for immutable note revisions and fact records, including required origin/source and revision constraints.

## Phase 2 — Generation path

- [ ] T005 Implement source resolution against the Spec 001 source contract, including immutable source version/reference lookup.
- [ ] T006 Implement the generation-adapter request and a strict structured-output schema; do not persist raw unvalidated output as success.
- [ ] T007 Implement deterministic fidelity checks for anchors, negation, uncertainty, attribution, numeric values, units, and unsupported diagnosis assertions.
- [ ] T008 Implement transactional persistence of generated draft, facts, and generation provenance with initial `DRAFT` status.
- [ ] T009 Implement `POST /api/v1/notes/generate` and controlled error mapping.

## Phase 3 — Import and revision paths

- [ ] T010 Implement imported draft persistence that records declared external provenance and never calls the generation adapter.
- [ ] T011 Implement `POST /api/v1/notes/import` with optional externally supplied facts and initial `DRAFT` status.
- [ ] T012 Implement editable-note revision creation with predecessor linkage; preserve the original revision unchanged.

## Phase 4 — Tests

- [ ] T013 Add deterministic regression fixtures and tests for GEN-001 through GEN-006 and GEN-010.
- [ ] T014 Add API/integration tests for GEN-007 and a spy assertion that imports never invoke generation.
- [ ] T015 Add malformed-output, timeout, and rollback tests for GEN-008.
- [ ] T016 Add draft-state/editability and revision-lineage tests for GEN-009 and metadata requirements.
- [ ] T017 Run the focused test suite, type/lint checks, migration validation, and the repository-required full suite.

## Phase 5 — Verification

- [ ] T018 Re-run `analyze.md` checks after any design adjustment and fix conflicts at their source.
- [ ] T019 Run the convergence review against `spec.md`, `plan.md`, and completed tasks; append only newly discovered gaps to this file.
