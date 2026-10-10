# Implementation Tasks — Spec 003

**Source artifacts:** `spec.md`, `clarify.md`, `plan.md`, AI Nursing Documentation Reliability Engine Constitution v1.0.0  
**Gate:** Do not start implementation until the reviewer has reviewed `checklist.md`. The implementation workflow must ask for direction if any reviewer-owned item remains unchecked; it must not alter the checklist.

**Constitution gate:** T011–T014 test fixtures must be written before T008 implementation begins. All fixtures, logs, screenshots, and evaluation inputs are synthetic-only.

## Dependency map

```text
T001–T003 foundation
        |
        +--> T004–T006 contract/validation --> T007 provider boundary
        |                                      |
        |                                      +--> T008 service/persistence --> T009 optional API
        |                                                                    |
        +--> T010–T014 automated tests --------+--> T015 security/docs --> T016 acceptance gate
```

## Phase 1 — Foundation

- [ ] T001 Confirm Python 3.12+, FastAPI, Pydantic v2, SQLite, pytest, dependency injection, error-format, synthetic-data, and protected-logging conventions. Create an ADR for a material cross-component decision that differs from `plan.md`. *(No dependency)*
- [ ] T002 Add/confirm immutable synthetic nursing-note revision access with UTF-8 body, body hash, revision id, language metadata, resident identity/status, and a transaction-safe read path. *(Depends on T001)*
- [ ] T003 Define application ports for note-revision loading, claim extraction provider, claim result persistence, and protected logging. *(Depends on T001)*

## Phase 2 — Domain contract and validation

- [ ] T004 Implement versioned Pydantic `ClaimCategory`, `Polarity`, `Certainty`, `Attribution`, `TextSpan`, `NumericValue`, `Claim`, resident-identity, and discriminated `ExtractionResult` contracts from `spec.md`; version/test OpenAPI if HTTP is exposed. *(Depends on T001)*
- [ ] T005 Implement Unicode code-point and UTF-16 offset conversion/validation against the immutable stored note body, including exact substring checks. *(Depends on T002, T004)*
- [ ] T006 Implement schema and semantic validation: revision match, unique ids, claim text/span equality, cue/value spans, numeric raw fidelity, attribution/negation evidence, and all-or-nothing failure behavior. *(Depends on T004, T005)*
- [ ] T007 Implement the dependency-injected provider adapter with Pydantic structured-output parsing, model/prompt/schema/settings version capture, explicit timeout/bounded retry, and no evidence-system connector. *(Depends on T003, T004)*

## Phase 3 — Extraction workflow and persistence (after test-first fixtures)

- [ ] T008 Implement `ClaimExtractionService.extract_claims(note_revision_id)`: load immutable synthetic revision, enforce German input policy, create idempotent run id, invoke provider, validate, distinguish `SUCCEEDED`/`EMPTY`/`FAILED`, and persist an atomic result. *(Depends on T002, T006, T007, T011–T014)*
- [ ] T009 If a public API is required by repository conventions, add `POST /api/v1/claims/extract` as a thin validated wrapper around the service, using established authentication/error conventions. *(Depends on T008)*
- [ ] T010 Implement SQLite result persistence/current-result lookup plus append-only logical run history scoped to exact note revision/body hash and version metadata; ensure a new revision cannot reuse an older result. *(Depends on T002, T004, T008)*

## Phase 4 — Automated tests (author T011–T014 before T008)

- [ ] T011 Write pytest contract/unit tests for result states, Pydantic schema validation, id uniqueness, resident identity, optional fields, raw numeric fidelity, and no verification/diagnosis fields. Ensure they fail before their implementation slice. *(Depends on T004, T006)*
- [ ] T012 Write Unicode/property tests for German diacritics, decimal comma, nested cues, overlapping claims, and invalid/mismatched code-point/UTF-16 spans. Ensure they fail before their implementation slice. *(Depends on T005, T006)*
- [ ] T013 Create versioned synthetic fixtures and expected service acceptance cases for CLM-001 through CLM-016, asserting exact structured attributes, source substrings, and run/revision provenance—not merely JSON. Start or extend the protected held-out corpus toward 100 labeled German scenarios. *(Depends on T004)*
- [ ] T014 Write failure-path test fixtures: unavailable/missing revision, changed body/revision, unsupported language, synthetic-data policy breach, malformed JSON, schema-invalid output, invalid span, provider timeout/retry, valid empty note, and transactional no-partial-claims behavior. *(Depends on T004, T006)*
- [ ] T015 Add optional HTTP adapter tests only if T009 is implemented. *(Depends on T009)*

## Phase 5 — Security, quality, and handoff

- [ ] T016 Verify synthetic-only data enforcement and error/telemetry redaction: production logs/errors contain no note body, prompt body, claim text, transcript, secret, or real personal data; permitted metrics retain only safe metadata. *(Depends on T008)*
- [ ] T017 Run formatting, static analysis, unit/property, Pydantic/OpenAPI contract, API (if applicable), CLM-001–CLM-016 acceptance, timeout/retry, and full 100+ synthetic benchmark suites. Retain raw counts, latency, cost/token usage where applicable, and failure examples. *(Depends on T011–T016)*
- [ ] T018 Conduct a scope review confirming no evidence retrieval, support/contradiction classification, clinical diagnosis, or medication inference was introduced. *(Depends on T017)*
- [ ] T019 Update traceability, re-run `analyze.md` review, and execute convergence audit. If gaps are found, append new tasks after T019 and repeat the implementation/convergence cycle. *(Depends on T018)*

## Parallelization guidance

After T004 is stable, T005 and T007 may proceed in parallel. After T008/T010, T011/T012 can run in parallel with preparation of the CLM fixture corpus; T013/T014 then verify the integrated service. Do not begin persistence, provider integration, or acceptance tests before the contract and span invariant decisions are implemented.
