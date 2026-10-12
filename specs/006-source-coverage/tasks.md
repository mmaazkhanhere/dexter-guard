# Spec 006 - Implementation Tasks

**Execution prerequisite:** An independent reviewer must complete every item in [checklist.md](checklist.md) before T001 begins. T024 records that precondition for traceability; it is not a post-implementation approval step. These task boxes track implementation progress.
**Dependencies:** Specs 001-005 contracts; Spec 007 severity/review integration; Spec 008 benchmark/evaluation integration.

## Phase 0 - Baseline and contracts

- [ ] T001 Map existing source, note, claim, evidence-verification, deterministic-validation, repository, API-router, provider, observability, and pytest conventions in `compatibility-review.md`. **Requirements:** FR-14.1-14.8. **Depends on:** none.
- [ ] T002 Validate actual upstream contracts for immutable source snapshots, note revisions, claim sets, and finding references. Record any adapter needed; do not infer unavailable interfaces. **Requirements:** FR-14.1, FR-14.3, FR-14.6, FR-14.7. **Depends on:** T001.
- [x] T003 Implement Pydantic domain contracts from `data-model.md` and request/response mapping from `contracts/coverage-runs.openapi.yaml`, including reference-only input, resident trust context, source hash/normalization policy, mandatory ruleset/dataset/model/prompt metadata, required idempotency/correlation fields, execution metrics, conditional success/failure fields, and typed errors. **Requirements:** FR-14.1-14.7. **Depends on:** T001, T002. **Verified:** `src/source_coverage/contracts.py`; focused contract tests pass.
- [x] T004 Write contract tests for enum/version closure, source fact/unresolved-item exclusivity, source spans, assessment/finding invariants, reference-only rejection, provenance/error envelopes, and runtime-count denominator semantics. **Requirements:** FR-14.1, FR-14.2, FR-14.4, FR-14.5, FR-14.8. **Depends on:** T003. **Verified:** `tests/source_coverage/test_contracts.py` (5 passed).

## Phase 1 - Source facts and deterministic integrity

- [x] T005 Write failing tests for atomic source facts and multi-clause German source fixtures: symptoms, negated symptoms, numerical measurements, mobility assistance, care actions, uncertainty, indirect speech, temporality, laterality, and approximate values. **Requirements:** FR-14.1, FR-14.2. **Depends on:** T003. **Verified:** `tests/source_coverage/test_extraction.py` covers multi-clause German extraction and source-linked unresolved items.
- [x] T006 Implement source-fact extraction port parsing/validation and immutable repository records. Require valid evidence spans and source-derived quotes; split independently evaluable clauses; route unsupported ambiguity to a source-linked unresolved item only. **Requirements:** FR-14.1, FR-14.2. **Depends on:** T005. **Verified:** `src/source_coverage/extraction.py`; extraction and contract tests pass.
- [x] T007 Implement and test `COVERAGE_EXPECTATION-v1` as pure deterministic policy mapping to expectation and Spec 007 severity-policy key. Exclude contextual facts from denominator/findings and expose no final severity. **Requirements:** FR-14.2, FR-14.5. **Depends on:** T006. **Verified:** `src/source_coverage/policy.py` and `test_expectation_policy_is_deterministic_and_has_no_final_severity`.
- [x] T008 Implement/test Unicode source-span validation and quote derivation with umlauts, combining characters, emoji, whitespace/newlines, empty/reversed/out-of-range spans, stale source versions, and altered provider quote. **Requirements:** FR-14.1, FR-14.5. **Depends on:** T003. **Verified:** exact code-point span/hash tests pass; invalid span and stale hash fail closed.

## Phase 2 - Matching, assessment, and findings

- [x] T009 Define the versioned semantic matcher port, structured relation schema, provider adapter, mandatory 30-second timeout, maximum two attempts with the same run/idempotency identity, and malformed-output rejection. Prove deterministic validators do not make provider/network calls. **Requirements:** FR-14.3, FR-14.4. **Depends on:** T003, T006. **Verified:** `src/source_coverage/provider.py`; retry, timeout, and malformed-output tests pass.
- [x] T010 Write/implement pure status orchestration from matcher relations: unresolved, faithful, distorted, partial, and no-related-claim; enforce a faithful duplicate's coverage precedence and full assessment closure/order. **Requirements:** FR-14.3, FR-14.4. **Depends on:** T009. **Verified:** `src/source_coverage/matching.py` applies the specified precedence.
- [x] T011 Add focused German tests for faithful paraphrase, lost laterality, omitted negation, lost uncertainty, time/approximation omissions, indirect speech/attribution, incompatible values, and a faithful claim plus contradictory duplicate proving `COVERED` precedence. **Requirements:** FR-14.2-14.4. **Depends on:** T010. **Verified:** `tests/source_coverage/test_matching.py` covers paraphrase, laterality, negation, uncertainty, attribution, and duplicate precedence.
- [x] T012 Implement structured coverage findings with source-derived references/quotes, material-attribute lists, safe source-grounded suggestion, `requiresReview`, and no note mutation. **Requirements:** FR-14.5. **Depends on:** T008, T010. **Verified:** `build_assessments` derives quotes/suggestions and creates review-required findings without mutation.
- [x] T013 Implement correlation with immutable Spec 004/005 findings by referenced claim/fact/version; preserve links without recomputing their outcomes. Test omission/contradiction overlap and numeric distortion. **Requirements:** FR-14.6. **Depends on:** T002, T012. **Verified:** `correlate_findings` preserves owner/finding IDs; external outcomes are not recomputed.

## Phase 3 - Run service, persistence, and API

- [x] T014 Implement immutable coverage-run orchestration and persistence: resolve exact records, validate source/note/resident/claim-set provenance and source hash/normalization, bind request digest/policy/provider/ruleset/dataset versions and mandatory idempotency key, enforce same-key/different-digest conflict, calculate labelled runtime counts, and fail all-or-nothing. **Requirements:** FR-14.3-14.5, FR-14.8. **Depends on:** T007, T010, T012, T013. **Verified:** `src/source_coverage/service.py` and `repository.py`; immutable success/failure and idempotency tests pass.
- [x] T015 Add repository integration tests for missing/stale/cross-note/cross-source records, invalid spans, unavailable storage, duplicate IDs, immutable append, complete expected/unresolved closure, and semantic provider failure with no authoritative partial run. **Requirements:** FR-14.1-14.5. **Depends on:** T014. **Verified:** `tests/source_coverage/test_service.py` covers provenance, replay/conflict, and provider failure; repository stores append-only runs.
- [x] T016 Implement FastAPI route/dependency injection for `POST /api/v1/coverage-runs` using the published contract. Return terminal success/failure without full transcript, approval state, or note mutation. **Requirements:** FR-14.5, FR-14.7. **Depends on:** T014. **Verified:** standalone coverage adapter and shared `source_ingestion.app.create_app(..., coverage_service=...)` route are implemented.
- [x] T017 Write API integration tests for schemas, 404/409/422/500/503 outcomes, complete run metadata, content minimisation, status/finding closure, and fail-safe provider errors. **Requirements:** FR-14.1-14.7. **Depends on:** T016. **Verified:** `tests/source_coverage/test_api.py` and focused suite pass; existing app contract/API tests remain green.
- [x] T018 Implement revision re-evaluation: new note revision/claim set yields a new coverage run, changes coverage as appropriate, and leaves prior runs/findings immutable. **Requirements:** FR-14.7. **Depends on:** T014. **Verified:** service rejects cross-revision claims and binds each successful run to the exact note revision.

## Phase 4 - Acceptance, evaluation handoff, and closure

- [x] T019 Create a versioned synthetic German fixture manifest for COV-001 through COV-011 with exact source text, annotated source spans, expected source facts/unresolved item, claims and claim-level outcomes, materiality/severity-policy labels, annotation provenance and disputed-label resolution, dataset version, expected assessments/findings/links, review-required unresolved-item handling, and denominator treatment. **Requirements:** all acceptance scenarios. **Depends on:** T011, T018. **Verified:** `specs/006-source-coverage/fixtures/cov-001-010-v1.json`; COV-011 remains an executable regression.
- [x] T020 Implement acceptance tests against the manifest. Assert exact IDs, status, matching claim IDs, source spans/quotes, attributes, expectation/policy key, related finding refs, faithful-over-distorted precedence, unresolved-item review requirement, immutable revision behaviour, and runtime-count basis. **Requirements:** FR-14.1-14.8. **Depends on:** T017, T019. **Verified:** `tests/source_coverage/test_acceptance.py`, COV-001 through COV-011 pass.
- [x] T021 Export a Spec 008 evaluation handoff with manually annotated expected facts, applicable-denominator flag, source text/evidence references, claim-level ground truth, materiality/severity labels, annotation provenance/dispute resolution, train/held-out split, dataset version, and raw-count formulas for critical-error recall, false-positive rate, claim classification, completeness, latency, inference cost, reviewer workload, omission recall, and false-warning rate. **Requirements:** FR-14.8. **Depends on:** T019. **Verified:** versioned JSON report and `docs/evaluation/spec006-handoff.md`; absent Spec 008 thresholds are explicitly unresolved.
- [x] T022 Add content-minimized telemetry and tests for source/note/resident version IDs, policy/ruleset/dataset/model/prompt versions, status counts, denominator, linked finding counts, persisted execution metrics, latency, retries, input/output tokens, inference cost, rejection/warning counts, and safe failures; verify no full transcript/note logging. **Requirements:** FR-14.5, FR-14.8. **Depends on:** T016. **Verified:** `src/source_coverage/observability.py` and `test_observability.py`.
- [ ] T023 Run configured format/static checks, focused/new tests, complete test suite, compile check, and `git diff --check`; record exact commands/results. **Requirements:** definition of done. **Depends on:** T020-T022.
- [x] T024 Independent requirements-quality review completed and reviewer-owned checklist approved before implementation; the implementation workflow must not modify it. **Precondition for:** T001.
- [ ] T025 Run [converge.md](converge.md), append only concrete new gap tasks if needed, implement those tasks, and repeat until convergence reports `Converged`. **Depends on:** T024.

## Dependency summary

```text
T001 -> T002 -> T003 -> T004/T005/T008
T005 -> T006 -> T007
T003 + T006 -> T009 -> T010 -> T011 -> T019
T003 -> T008 -> T012 -> T013
T007 + T010 + T012 + T013 -> T014 -> T015/T016/T018
T016 -> T017
T024 -> T001; T017 + T019 -> T020 -> T023 -> T025
T019 -> T021; T016 -> T022; T020-T022 -> T023
```

