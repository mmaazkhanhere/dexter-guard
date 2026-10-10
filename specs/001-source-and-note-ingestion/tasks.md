<!--
# Legacy task list retained for review history. It is superseded by the
Spec Kit-compliant task list below.

# Tasks: Source and Note Ingestion

## Contract and schema

- [ ] Define the `SourceDocument` contract with source ID, version, resident test ID, language, transcript text, and creation timestamp.
- [ ] Define the `SourceSpan` value object with source ID, source version, inclusive start, and exclusive end offsets.
- [ ] Document the zero-based character-offset convention.
- [ ] Document the immutable source/version identity `(source_id, source_version)`.
- [ ] Add contract fixtures usable by downstream specifications.

## Validation

- [ ] Validate that the request is structurally well formed.
- [ ] Validate that transcript input is text.
- [ ] Reject missing, blank, and whitespace-only transcripts.
- [ ] Validate a single synthetic `resident_test_id`.
- [ ] Enforce `language = de-DE` for this proof of concept.
- [ ] Reject unsupported audio and other non-text input.
- [ ] Reject multi-resident submissions according to the selected request schema.
- [ ] Return stable structured validation errors with code, message, and field/path.
- [ ] Ensure invalid submissions do not create partial persistence records.

## Identification and versioning

- [ ] Generate a unique source ID for every initial accepted transcript.
- [ ] Start each new source at version 1.
- [ ] Implement an explicit operation for creating the next version of an existing source.
- [ ] Preserve every previous source version without overwriting.
- [ ] Reject duplicate source/version identities.
- [ ] Keep the resident test ID stable across versions of the same source.

## Persistence and retrieval

- [ ] Add a repository abstraction for source documents.
- [ ] Persist the exact original transcript text.
- [ ] Support retrieval by `source_id` and `source_version`.
- [ ] Return a structured not-found error for missing sources and versions.
- [ ] Verify that retrieval returns the stored text without normalization or correction.

## Source spans

- [ ] Validate that the referenced source exists.
- [ ] Validate that the referenced source version exists.
- [ ] Reject negative offsets.
- [ ] Reject zero-length spans.
- [ ] Reject reversed spans.
- [ ] Reject end offsets beyond the exact transcript version.
- [ ] Reject cross-version or stale references.
- [ ] Resolve valid spans as derived excerpts while retaining the authoritative source reference.

## API/demo integration

- [ ] Expose new transcript submission through the existing demo/API convention.
- [ ] Expose explicit source-version creation.
- [ ] Expose source retrieval by ID and version.
- [ ] Expose source-span validation or resolution.
- [ ] Return source identity and version in successful responses.
- [ ] Return structured errors for all documented rejection cases.

## Tests

- [ ] Add a valid German transcript acceptance test.
- [ ] Add blank and whitespace-only transcript tests.
- [ ] Add malformed request and non-text input tests.
- [ ] Add unique source ID tests.
- [ ] Add exactly-one-resident association tests.
- [ ] Add exact text round-trip tests using German characters and line breaks.
- [ ] Add version preservation and historical retrieval tests.
- [ ] Add valid source-span tests.
- [ ] Add invalid span boundary tests.
- [ ] Add missing source/version tests.
- [ ] Add audio and multi-resident exclusion tests.
- [ ] Verify the test suite runs without an LLM provider or network call.

## Scope guard

- [ ] Confirm no LLM SDK, provider, prompt, or medical reasoning is required by this specification.
- [ ] Confirm no speech recognition or audio pipeline is introduced.
- [ ] Confirm no multi-resident disambiguation is introduced.
- [ ] Confirm no production authentication or authorization is introduced.
- [ ] Confirm domain-specific fields for notes, facts, claims, findings, reviews, and evaluation cases remain owned by their respective specifications.
-->

# Tasks: Source Transcript Ingestion and Evidence Reference Foundation

Input: `specs/001-source-and-note-ingestion/spec.md`, `specs/001-source-and-note-ingestion/plan.md`, `specs/001-source-and-note-ingestion/data-model.md`, `specs/001-source-and-note-ingestion/contracts/source-api.yaml`

Tests: Required by the feature specification. All tests must run without an LLM provider, audio pipeline, network dependency, or medical reasoning service.

Task format: `- [ ] [TaskID] [P?] [Story?] Description with exact file path`

## Dependencies

```text
T001 -> T002 -> T003 -> T004
T004 -> T005 -> T006 -> T007
T007 -> T008 -> T009 -> T010
T007 -> T011 -> T012
T010 -> T013
T012 -> T013
T013 -> T014
```

User story order: US1 (ingest) -> US2 (version) -> US3 (spans). US2 depends on the source contract and repository foundation from US1. US3 depends on source retrieval from US1 and version identity from US2.

## Phase 1: Setup

**Purpose**: Establish documentation and test locations without selecting an unconfirmed application stack.

- [ ] T001 Confirm the Python package layout uses `src/source_ingestion/` and `tests/source_ingestion/`, and record any required adjustment in `specs/001-source-and-note-ingestion/plan.md` before implementation.
- [ ] T002 [P] Add the source contract fixture location at `tests/fixtures/source-ingestion/valid-german-transcript.json`.

## Phase 2: Foundational

**Purpose**: Implement blocking source-contract, error, repository, and concurrency foundations before user-story work.

- [ ] T003 Define `SourceDocument` and `SourceSpan` runtime types in `src/source_ingestion/contracts.py` from `specs/001-source-and-note-ingestion/data-model.md`, preserving required fields and Unicode scalar-value offset semantics.
- [ ] T004 [P] Define structured source errors, including `INVALID_REQUEST`, `INVALID_TRANSCRIPT`, `INVALID_RESIDENT_TEST_ID`, `SOURCE_NOT_FOUND`, `SOURCE_VERSION_NOT_FOUND`, `INVALID_SOURCE_SPAN`, and `VERSION_CONFLICT`, in `src/source_ingestion/errors.py`.
- [ ] T005 Create the repository interface in `src/source_ingestion/repository.py` with atomic create, next-version, get-by-composite-key, and existence operations.
- [ ] T006 [P] Add the OpenAPI contract check for `specs/001-source-and-note-ingestion/contracts/source-api.yaml` and verify the documented request/response schemas agree with the data model.

## Phase 3: User Story 1 - Submit an identifiable German transcript (P1)

**Goal**: Accept one structured German transcript with one scalar synthetic resident ID and persist exact source text as version 1.

**Independent test criteria**: A valid request returns a unique source ID and version 1; blank, non-text, malformed, repeated, or array-valued resident input returns a structured error and creates no record; exact Unicode text round-trips unchanged.

- [ ] T007 [US1] Add API/schema tests in `tests/source_ingestion/test_source_submission.*` for FR-01, AC-001, AC-002, AC-003, AC-004, AC-005, and AC-011.
- [ ] T008 [US1] Implement structured request validation in `src/source_ingestion/validation.py`: require exactly one scalar `resident_test_id`, `language: de-DE`, and non-blank string `transcript_text`; do not infer residents from transcript content.
- [ ] T009 [US1] Implement initial source creation in `src/source_ingestion/service.py`: generate a unique `source_id`, assign `source_version: 1`, preserve text exactly, and persist atomically.
- [ ] T010 [US1] Add API integration coverage in `tests/source_ingestion/test_source_submission.*` proving no partial record is persisted after validation failure and no LLM provider is called.

## Phase 4: User Story 2 - Preserve and retrieve source versions (P1)

**Goal**: Create immutable revisions, preserve historical versions, and reject stale concurrent writes.

**Independent test criteria**: A revision with the current expected version creates exactly one next version; two revisions with the same expected version result in one success and one `409 VERSION_CONFLICT`; both historical versions remain retrievable.

- [ ] T011 [US2] Add versioning and concurrency tests in `tests/source_ingestion/test_source_versioning.*` for AC-006, AC-009, and the atomic-write/evidence-integrity invariants.
- [ ] T012 [US2] Implement version creation in `src/source_ingestion/service.py` using `expected_source_version`, a single transaction, and uniqueness on `(source_id, source_version)`; inherit resident ID and language from the existing source.
- [ ] T013 [US2] Implement retrieval by `(source_id, source_version)` and map stale expected versions or uniqueness races to `VERSION_CONFLICT` without partial persistence in `src/source_ingestion/repository.py`.

## Phase 5: User Story 3 - Reference exact evidence spans (P1)

**Goal**: Validate and resolve spans against exact source versions using Unicode scalar-value indices.

**Independent test criteria**: Valid spans resolve with inclusive start and exclusive end; offsets count Unicode scalar values rather than bytes, UTF-16 units, or grapheme clusters; invalid and missing references fail deterministically.

- [ ] T014 [US3] Add span boundary and Unicode tests in `tests/source_ingestion/test_source_spans.*` for AC-007, AC-008, AC-009, and the no-cross-version-redirection invariant.
- [ ] T015 [US3] Implement `SourceSpan` validation and resolution in `src/source_ingestion/spans.py`: enforce `0 <= start < end <= unicode_scalar_value_length(transcript_text)` for the referenced version.
- [ ] T016 [US3] Add API integration coverage in `tests/source_ingestion/test_source_spans.*` for missing sources, missing versions, negative/empty/reversed/out-of-range spans, combining marks, CRLF, and non-ASCII German text.

## Phase 6: Polish and cross-cutting verification

- [ ] T017 [P] Validate that `specs/001-source-and-note-ingestion/contracts/source-api.yaml` matches `specs/001-source-and-note-ingestion/data-model.md` and `specs/001-source-and-note-ingestion/spec.md`.
- [ ] T018 [P] Add the FR-01 and evidence-integrity traceability matrix to `tests/source_ingestion/README.md`.
- [ ] T019 Run the source-ingestion test suite from the project’s documented command and record that it does not call an LLM in `specs/001-source-and-note-ingestion/plan.md`.
- [ ] T020 Confirm no authentication, speech recognition, multi-resident processing, clinical reasoning, or external nursing-note ingestion is introduced in the implementation files identified by `specs/001-source-and-note-ingestion/plan.md`.

## Parallel execution opportunities

- T002, T004, and T006 can run in parallel after T001.
- T007 and T011 can be prepared in parallel after the foundational contracts are agreed.
- T014 and T017 can run in parallel after the API and data model are stable.
- T018 and T020 can run in parallel during polish.

## MVP scope

The MVP is User Story 1 plus the foundational tasks T001-T010. User Story 2 is required before any revision workflow is exposed, and User Story 3 is required before downstream evidence-bearing components consume spans.
