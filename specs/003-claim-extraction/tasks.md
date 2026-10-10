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

## Phase 1 — Foundation

- [ ] T001 Confirm Python 3.12+, FastAPI, Pydantic v2, SQLite, pytest, dependency injection, error-format, synthetic-data, and protected-logging conventions. Create an ADR for a material cross-component decision that differs from `plan.md`. *(No dependency)*
- [ ] T002 Add/confirm immutable synthetic nursing-note revision access with UTF-8 body, body hash, revision id, language metadata, resident identity/status, and a transaction-safe read path. *(Depends on T001)*
- [ ] T003 Define application ports for note-revision loading, claim extraction provider, claim result persistence, and protected logging. *(Depends on T001)*

## Phase 2 — Test-first contracts and fixtures

- [ ] T004 Write failing Pydantic contract tests for the versioned Claim/result union, required/forbidden failed-result fields, exact `Decimal` serialization, resident identity, source-reference, and OpenAPI expectations if HTTP is exposed. *(Depends on T001)*
- [ ] T005 Write failing Unicode/property tests for code-point/UTF-16 span conversion, exact stored-body substring/body-hash checks, German diacritics, decimal commas, nested cues, overlaps, and malformed offsets. *(Depends on T002)*
- [ ] T006 Create versioned synthetic CLM-001–CLM-016 fixtures and negative cases with expected semantic fields, source substrings, source/evidence references, materiality/severity, annotation provenance, and held-out membership. *(Depends on T001)*
- [ ] T007 Write fake-provider/outbox tests for structured Pydantic output, model/prompt/schema/settings provenance, timeout/bounded retry, typed failures, `ClaimExtractionCompleted`, and no evidence-system connector. *(Depends on T003)*

## Phase 3 — Contract, validator, provider, and service implementation

- [ ] T008 Implement the versioned Pydantic `ClaimCategory`, `Polarity`, `Certainty`, `Attribution`, `TextSpan`, `NumericValue`, `Claim`, resident-identity, source-reference, and discriminated `ExtractionResult` contracts tested by T004. *(Depends on T004)*
- [ ] T009 Implement Unicode code-point/UTF-16 conversion and immutable stored-body span validation tested by T005. *(Depends on T005, T008)*
- [ ] T010 Implement schema/semantic validation: revision and identity match, unique ids, claim/span equality, cue/value spans, exact `Decimal` normalization, no forbidden evidence fields, and all-or-nothing behavior. *(Depends on T006, T008, T009)*
- [ ] T011 Implement the dependency-injected provider adapter tested by T007, including Pydantic parsing, provenance capture, timeout/bounded retry, and no evidence connector. *(Depends on T007, T008)*
- [ ] T012 Implement `ClaimExtractionService.extract_claims(note_revision_id)`: enforce German/synthetic/50,000-code-point guards, create idempotent runs, invoke provider, validate, distinguish outcomes, and emit the completion handoff. *(Depends on T002, T006, T010, T011)*

## Phase 4 — Persistence and optional API implementation

- [ ] T013 Implement SQLite result/current-result lookup, append-only run history, and transactional `ClaimExtractionCompleted` outbox scoped to exact revision/body hash/source reference/version metadata. *(Depends on T002, T008, T012)*
- [ ] T014 If HTTP is exposed, add `POST /api/v1/claims/extract` as a thin FastAPI wrapper with a versioned OpenAPI artifact, bounded request schema, and established authentication/error conventions. *(Depends on T012)*

## Phase 5 — Security, quality, and handoff

- [ ] T015 Run CLM-001–CLM-016 service acceptance, failure-path, transaction/outbox, and FastAPI/OpenAPI tests when T014 applies; assert exact semantics, handoff metadata, and no evidence verdicts. *(Depends on T012, T013, T014 if applicable)*
- [ ] T016 Verify 50,000-code-point input enforcement, synthetic-only data enforcement, error/telemetry redaction, secret scanning, and dependency-vulnerability checks. *(Depends on T012, T013)*
- [ ] T017 Run the versioned 100+ benchmark and report denominators, precision/recall, critical-error recall, false-positive rate, completeness, latency, cost/token usage, reviewer workload, raw counts, and representative failures; enforce Spec 008 thresholds. *(Depends on T015, T016)*
- [ ] T018 Conduct a scope review confirming no evidence retrieval, support/contradiction classification, clinical diagnosis, or medication inference was introduced. *(Depends on T017)*
- [ ] T019 Update traceability, re-run `analyze.md` review, and execute convergence audit. If gaps are found, append new tasks after T019 and repeat the implementation/convergence cycle. *(Depends on T018)*

## Parallelization guidance

After T001–T003, T004–T007 may proceed in parallel. T008–T011 may proceed as their prerequisites complete; T012 follows the integrated validator/provider path. T013 and optional T014 then proceed in parallel, followed by T015–T019. No implementation task begins before its corresponding failing test/fixture task.
