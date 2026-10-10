# Tasks: Nursing Note Generation

**Gate:** The reviewer-owned `checklist.md` remains a requirements-quality artifact. Implementation follows the approved constitution, specification, plan, data model, and API contract.

## Foundational contracts

- [x] T001 Read `.specify/memory/constitution.md` and record its applicable constraints in `plan.md`.
- [x] T002 [P] Validate and finalize `data-model.md` and `contracts/notes-api.yaml` against the Spec 001 `SourceDocument` contract.
- [x] T003 Create runtime request/result schemas in `src/nursing_notes/contracts.py`.
- [x] T004 Create immutable revision and fact persistence in `src/nursing_notes/repository.py`; enforce non-null source ID/version.
- [x] T004a [P] Create the ADR in `docs/adr/002-nursing-note-generation-boundaries.md` covering Python/FastAPI/Pydantic and adapter trade-offs.

## User story 1 — Generate an editable draft (FR-02, GEN-001, GEN-009)

**Independent test:** A known transcript/version returns one editable German `DRAFT`, never a verified or approved note.

- [x] T005 [US1] Implement source-version resolution in `src/nursing_notes/service.py`.
- [x] T006 [US1] Implement provider invocation in `src/nursing_notes/adapters.py` using the adapter protocol.
- [x] T007 [US1] Implement transactional generated-draft creation in `src/nursing_notes/service.py`.
- [x] T008 [US1] Implement `POST /api/v1/notes/generate` in `src/source_ingestion/app.py`.
- [x] T009 [US1] Add GEN-001/GEN-009 API and service tests in `tests/nursing_notes/test_notes_api.py`.

## User story 2 — Obtain structured source-linked facts (FR-03, GEN-002–GEN-006, GEN-008, GEN-010)

**Independent test:** Fixed fixtures return source-linked facts with exact expected field outcomes; malformed/prohibited fixtures persist nothing.

- [x] T010 [US2] Implement generation-result schema validation in `src/nursing_notes/contracts.py` and `src/nursing_notes/service.py`.
- [x] T011 [US2] Implement bounded source-anchor/value/unit/fidelity-field guardrails in `src/nursing_notes/guardrails.py`.
- [x] T012 [US2] Persist facts atomically with a generated revision in `src/nursing_notes/repository.py`.
- [x] T013 [US2] Add GEN-002–GEN-006 fixture regressions in `tests/nursing_notes/test_notes_api.py`.
- [x] T014 [US2] Add GEN-008 rollback and GEN-010 guardrail regressions in `tests/nursing_notes/test_notes_api.py`.
- [x] T014a [US2] Add source-anchor, resident `UNKNOWN`, source-offset, and validation-run provenance coverage in `tests/nursing_notes/test_notes_api.py` and `test_contracts.py`.

## User story 3 — Import an external candidate against its evidence source (FR-04, GEN-007)

**Independent test:** An external candidate with a resolvable source/version is stored as an imported `DRAFT`; its external origin is retained and the generation adapter is called zero times.

- [x] T015 [US3] Implement import validation requiring source ID/version and external origin in `src/nursing_notes/service.py`.
- [x] T016 [US3] Implement imported revision persistence with distinct external-origin/evidence-source fields in `src/nursing_notes/repository.py`.
- [x] T017 [US3] Implement `POST /api/v1/notes/import` in `src/source_ingestion/app.py`.
- [x] T018 [US3] Add GEN-007, source-version, and zero-adapter-call tests in `tests/nursing_notes/test_notes_api.py`.

## Cross-cutting verification

- [x] T019 Implement revision editing with immutable predecessor linkage in `src/nursing_notes/service.py` and test it in `tests/nursing_notes/test_notes_api.py`.
- [x] T020 Run contract, focused fixture, syntax, and repository-required test suites; record results in `specs/002-nursing-note-generation/implement.md`.
- [x] T021 Re-run the Spec 002 artifact consistency and convergence review; record the result in `implement.md`.
- [x] T022 Run the synthetic-only observability tests for timeout, bounded retry, idempotent run ID, rejection metrics, and content-free telemetry; link the full 100-scenario evaluation to `008-evaluation.md` rather than claiming it here.

## Reviewer remediation

- [x] R001 Replace the application-default in-memory note store with SQLite while retaining the in-memory implementation as an explicit test double; cover durable round-trip and append-only revision behavior in `tests/nursing_notes/test_repository.py`.
- [x] R002 Align the OpenAPI contract and runtime response/error behavior.
- [x] R003 Add unit-mutation, material source-span omission, and draft-to-source mismatch fixtures.
- [x] R004 Strengthen fact provenance/atomicity validation and make provider timeout/retry execution non-overlapping.
