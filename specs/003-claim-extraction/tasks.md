# Implementation Tasks — Spec 003

**Source artifacts:** `spec.md`, `clarify.md`, `plan.md`, AI Nursing Documentation Reliability Engine Constitution v1.0.0  
**Gate:** Do not start implementation until the reviewer has reviewed `checklist.md`. The implementation workflow must ask for direction if any reviewer-owned item remains unchecked; it must not alter the checklist.

**Constitution gate:** T004–T007 test fixtures must be written before their corresponding implementation tasks T008–T012 begin. All fixtures, logs, screenshots, and evaluation inputs are synthetic-only.

## Dependency map

```text
T001–T003 foundation --> T004–T007 test-first contracts/fixtures
                                      |
                                      v
                           T008–T012 contract/provider/service implementation
                                      |
                                      v
                                T013–T014 persistence/API
                                      |
                                      v
                             T015–T017 acceptance/evaluation/security
                                      |
                                      v
                                    T018–T019 handoff
```

## Phase 1 — Setup

- [x] T001 Record approved implementation conventions in `specs/003-claim-extraction/plan.md`; create `docs/adr/003-claim-extraction-boundaries.md` only for a material cross-component deviation. *(No dependency)*
- [x] T002 Add immutable note-revision access in `src/claim_extraction/revision_reader.py`, requiring source reference and one `resident_test_id`; reject missing associations. *(Depends on T001)*
- [x] T003 Define provider, result-repository, and logger ports in `src/claim_extraction/ports.py`. *(Depends on T001)*

## Phase 2 — Foundational contracts and fixtures

- [x] T004 [P] Write failing contract tests in `tests/claim_extraction/test_models.py` for Claim/result variants, source provenance, resident test ID, and typed failures. *(Depends on T001)*
- [x] T005 [P] Write failing span/property tests in `tests/claim_extraction/test_spans.py` for German text, decimal commas, overlap, and invalid offsets. *(Depends on T002)*
- [x] T006 [P] Create synthetic CLM-001–CLM-016 fixtures in `tests/claim_extraction/fixtures/claims.py` and benchmark-contribution cases in `tests/evaluation/fixtures/spec_003_claims.py`. *(Depends on T001)*
- [x] T007 [P] Write fake-provider and persisted-result tests in `tests/claim_extraction/test_provider.py` for malformed output, timeout, retry, and no evidence-system call. *(Depends on T003)*

## Phase 3 — User Story 1: Extract independently addressable atomic claims

**Independent test:** Given a stored candidate note, CLM-001 through CLM-003 return every independently verifiable assertion with a unique id and exact note span.

- [x] T008 [US1] Implement Claim/result contracts in `src/claim_extraction/models.py`. *(Depends on T004)*
- [x] T009 [US1] Implement span resolution in `src/claim_extraction/spans.py`. *(Depends on T005, T008)*
- [x] T010 [US1] Implement atomicity, revision, and span validation in `src/claim_extraction/validator.py`. *(Depends on T006, T008, T009)*

## Phase 4 — User Story 2: Preserve claim semantics without inference

**Independent test:** CLM-004 through CLM-010 and CLM-014 preserve negation, certainty, attribution, time, values, units, medication details, and clinical conclusions without an evidence verdict.

- [x] T011 [US2] Implement provider parsing and semantic-field validation in `src/claim_extraction/provider.py`. *(Depends on T007, T008, T010)*

## Phase 5 — User Story 3: Expose safe, revision-bound results for verification

**Independent test:** CLM-011 through CLM-013a, CLM-015, and CLM-016 return correct revision-bound success/empty/failure outcomes; Spec 004 retrieves the typed persisted result.

- [x] T012 [US3] Implement extraction orchestration and bounded empty-result safeguard in `src/claim_extraction/service.py`. *(Depends on T002, T006, T010, T011)*

## Phase 6 — Polish and cross-cutting quality

- [x] T013 [US3] Implement SQLite result persistence and current-result retrieval in `src/claim_extraction/repository.py`. *(Depends on T002, T008, T012)*
- [ ] T014 [US3] If HTTP is exposed, add FastAPI adapter `src/claim_extraction/api.py` and `specs/003-claim-extraction/contracts/claims-api.yaml`. *(Depends on T012)*

- [ ] T015 Run service acceptance in `tests/claim_extraction/test_service.py` for CLM-001–CLM-016 and failure paths; add API contract tests in `tests/claim_extraction/test_api.py` only if T014 applies. *(Depends on T012, T013, T014 if applicable)*
- [x] T016 [P] Verify synthetic-only fixtures and redacted telemetry in `tests/claim_extraction/test_observability.py`. *(Depends on T012, T013)*
- [ ] T017 Contribute Spec 003 fixtures and extraction metrics to `specs/008-evaluation.md` and its shared benchmark suite. *(Depends on T015, T016)*
- [ ] T018 Conduct scope review in `specs/003-claim-extraction/converge.md`, confirming no source-evidence alignment, diagnosis, identity inference, or distributed delivery was introduced. *(Depends on T017)*
- [ ] T019 Update traceability in `specs/003-claim-extraction/analyze.md` and execute convergence review. *(Depends on T018)*

## Parallelization guidance

After T001–T003, T004–T007 may proceed in parallel. Each user-story phase is independently testable before the next phase begins. No implementation task begins before its corresponding failing test/fixture task.
