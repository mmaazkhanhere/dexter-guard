# Tasks: Nursing Note Generation

**Gate:** Reviewer completion of `checklist.md` is required before implementation. Task paths below are planned feature paths; map them to constitution-approved repository equivalents only if the existing layout requires it.

## Foundational contracts

- [ ] T001 Read `.specify/memory/constitution.md` and record its applicable constraints in `specs/002-nursing-note-generation/plan.md` before code changes.
- [ ] T002 [P] Validate and finalize `specs/002-nursing-note-generation/data-model.md` and `specs/002-nursing-note-generation/contracts/notes-api.yaml` against the Spec 001 `SourceDocument` contract.
- [ ] T003 Create runtime request/result schemas in `src/features/notes/contracts.ts` from `contracts/notes-api.yaml`.
- [ ] T004 Create immutable revision and fact persistence/migration in `src/features/notes/note-repository.ts` and the repository migration directory; enforce non-null `sourceId` and `sourceVersion`.

## User story 1 — Generate an editable draft (FR-02, GEN-001, GEN-009)

**Independent test:** A known transcript/version returns one editable German `DRAFT`, never a verified or approved note.

- [ ] T005 [US1] Implement source-version resolution in `src/features/notes/source-resolver.ts`.
- [ ] T006 [US1] Implement provider invocation in `src/features/notes/generation-service.ts` using the repository-approved adapter.
- [ ] T007 [US1] Implement transactional generated-draft creation in `src/features/notes/note-service.ts`.
- [ ] T008 [US1] Implement `POST /api/v1/notes/generate` in `src/features/notes/notes-routes.ts`.
- [ ] T009 [US1] Add GEN-001/GEN-009 API and service tests in `test/features/notes/generate-draft.spec.ts`.

## User story 2 — Obtain structured source-linked facts (FR-03, GEN-002–GEN-006, GEN-008, GEN-010)

**Independent test:** Fixed fixtures return source-linked facts with exact expected field outcomes; malformed/prohibited fixtures persist nothing.

- [ ] T010 [US2] Implement generation-result schema validation in `src/features/notes/generation-schema.ts`.
- [ ] T011 [US2] Implement limited source-anchor/value/unit/fidelity-field guardrails in `src/features/notes/generation-guardrails.ts`.
- [ ] T012 [US2] Persist facts atomically with a generated revision in `src/features/notes/note-repository.ts`.
- [ ] T013 [US2] Add GEN-002–GEN-006 fixture regressions in `test/features/notes/fidelity-fixtures.spec.ts`.
- [ ] T014 [US2] Add GEN-008 rollback and GEN-010 limited-guardrail regressions in `test/features/notes/generation-failure.spec.ts`.

## User story 3 — Import an external candidate against its evidence source (FR-04, GEN-007)

**Independent test:** An external candidate with a resolvable source/version is stored as an imported `DRAFT`; its external origin is retained and the generation adapter is called zero times.

- [ ] T015 [US3] Implement import validation requiring source ID/version and external origin in `src/features/notes/import-service.ts`.
- [ ] T016 [US3] Implement imported revision persistence with distinct external-origin/evidence-source fields in `src/features/notes/note-repository.ts`.
- [ ] T017 [US3] Implement `POST /api/v1/notes/import` in `src/features/notes/notes-routes.ts`.
- [ ] T018 [US3] Add GEN-007, unknown/mismatched source-version, and zero-adapter-call tests in `test/features/notes/import-note.spec.ts`.

## Cross-cutting verification

- [ ] T019 Implement revision editing with immutable predecessor linkage in `src/features/notes/note-service.ts` and test it in `test/features/notes/note-revisions.spec.ts`.
- [ ] T020 Run contract, focused fixture, migration, type/lint, and repository-required test suites; record results in `specs/002-nursing-note-generation/implement.md`.
- [ ] T021 Re-run `analyze.md`, then `converge.md`; append any discovered dependency-ordered gaps to this file.
