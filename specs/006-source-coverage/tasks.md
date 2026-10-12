# Spec 006 - Implementation Tasks

**Execution prerequisite:** An independent reviewer must complete every item in [checklist.md](checklist.md). These task boxes track implementation progress and are intentionally open.  
**Dependencies:** Specs 001-005 contracts; Spec 007 severity/review integration; Spec 008 benchmark/evaluation integration.

## Phase 0 - Baseline and contracts

- [ ] T001 Map existing source, note, claim, evidence-verification, deterministic-validation, repository, API-router, provider, observability, and pytest conventions in `compatibility-review.md`. **Requirements:** FR-14.1-14.8. **Depends on:** none.
- [ ] T002 Validate actual upstream contracts for immutable source snapshots, note revisions, claim sets, and finding references. Record any adapter needed; do not infer unavailable interfaces. **Requirements:** FR-14.1, FR-14.3, FR-14.6, FR-14.7. **Depends on:** T001.
- [ ] T003 Implement Pydantic domain contracts from `data-model.md` and request/response mapping from `contracts/coverage-runs.openapi.yaml`, including reference-only input, resident trust context, source hash/normalization policy, mandatory ruleset/dataset/model/prompt metadata, required idempotency/correlation fields, execution metrics, conditional success/failure fields, and typed errors. **Requirements:** FR-14.1-14.7. **Depends on:** T001, T002.
- [ ] T004 Write contract tests for enum/version closure, source fact/unresolved-item exclusivity, source spans, assessment/finding invariants, reference-only rejection, provenance/error envelopes, and runtime-count denominator semantics. **Requirements:** FR-14.1, FR-14.2, FR-14.4, FR-14.5, FR-14.8. **Depends on:** T003.

## Phase 1 - Source facts and deterministic integrity

- [ ] T005 Write failing tests for atomic source facts and multi-clause German source fixtures: symptoms, negated symptoms, numerical measurements, mobility assistance, care actions, uncertainty, indirect speech, temporality, laterality, and approximate values. **Requirements:** FR-14.1, FR-14.2. **Depends on:** T003.
- [ ] T006 Implement source-fact extraction port parsing/validation and immutable repository records. Require valid evidence spans and source-derived quotes; split independently evaluable clauses; route unsupported ambiguity to a source-linked unresolved item only. **Requirements:** FR-14.1, FR-14.2. **Depends on:** T005.
- [ ] T007 Implement and test `COVERAGE_EXPECTATION-v1` as pure deterministic policy mapping to expectation and Spec 007 severity-policy key. Exclude contextual facts from denominator/findings and expose no final severity. **Requirements:** FR-14.2, FR-14.5. **Depends on:** T006.
- [ ] T008 Implement/test Unicode source-span validation and quote derivation with umlauts, combining characters, emoji, whitespace/newlines, empty/reversed/out-of-range spans, stale source versions, and altered provider quote. **Requirements:** FR-14.1, FR-14.5. **Depends on:** T003.

## Phase 2 - Matching, assessment, and findings

- [ ] T009 Define the versioned semantic matcher port, structured relation schema, provider adapter, mandatory 30-second timeout, maximum two attempts with the same run/idempotency identity, and malformed-output rejection. Prove deterministic validators do not make provider/network calls. **Requirements:** FR-14.3, FR-14.4. **Depends on:** T003, T006.
- [ ] T010 Write/implement pure status orchestration from matcher relations: unresolved, faithful, distorted, partial, and no-related-claim; enforce a faithful duplicate's coverage precedence and full assessment closure/order. **Requirements:** FR-14.3, FR-14.4. **Depends on:** T009.
- [ ] T011 Add focused German tests for faithful paraphrase, lost laterality, omitted negation, lost uncertainty, time/approximation omissions, indirect speech/attribution, and incompatible values. **Requirements:** FR-14.2-14.4. **Depends on:** T010.
- [ ] T012 Implement structured coverage findings with source-derived references/quotes, material-attribute lists, safe source-grounded suggestion, `requiresReview`, and no note mutation. **Requirements:** FR-14.5. **Depends on:** T008, T010.
- [ ] T013 Implement correlation with immutable Spec 004/005 findings by referenced claim/fact/version; preserve links without recomputing their outcomes. Test omission/contradiction overlap and numeric distortion. **Requirements:** FR-14.6. **Depends on:** T002, T012.

## Phase 3 - Run service, persistence, and API

- [ ] T014 Implement immutable coverage-run orchestration and persistence: resolve exact records, validate source/note/resident/claim-set provenance and source hash/normalization, bind request digest/policy/provider/ruleset/dataset versions and mandatory idempotency key, enforce same-key/different-digest conflict, calculate labelled runtime counts, and fail all-or-nothing. **Requirements:** FR-14.3-14.5, FR-14.8. **Depends on:** T007, T010, T012, T013.
- [ ] T015 Add repository integration tests for missing/stale/cross-note/cross-source records, invalid spans, unavailable storage, duplicate IDs, immutable append, complete expected/unresolved closure, and semantic provider failure with no authoritative partial run. **Requirements:** FR-14.1-14.5. **Depends on:** T014.
- [ ] T016 Implement FastAPI route/dependency injection for `POST /api/v1/coverage-runs` using the published contract. Return terminal success/failure without full transcript, approval state, or note mutation. **Requirements:** FR-14.5, FR-14.7. **Depends on:** T014.
- [ ] T017 Write API integration tests for schemas, 404/409/422/500/503 outcomes, complete run metadata, content minimisation, status/finding closure, and fail-safe provider errors. **Requirements:** FR-14.1-14.7. **Depends on:** T016.
- [ ] T018 Implement revision re-evaluation: new note revision/claim set yields a new coverage run, changes coverage as appropriate, and leaves prior runs/findings immutable. **Requirements:** FR-14.7. **Depends on:** T014.

## Phase 4 - Acceptance, evaluation handoff, and closure

- [ ] T019 Create a versioned synthetic German fixture manifest for COV-001 through COV-010 with exact source text, annotated source spans, expected source facts/unresolved item, claims and claim-level outcomes, materiality/severity-policy labels, annotation provenance and disputed-label resolution, dataset version, expected assessments/findings/links, and denominator treatment. **Requirements:** all acceptance scenarios. **Depends on:** T011, T018.
- [ ] T020 Implement acceptance tests against the manifest. Assert exact IDs, status, matching claim IDs, source spans/quotes, attributes, expectation/policy key, related finding refs, immutable revision behaviour, and runtime-count basis. **Requirements:** FR-14.1-14.8. **Depends on:** T017, T019.
- [ ] T021 Export a Spec 008 evaluation handoff with manually annotated expected facts, applicable-denominator flag, source text/evidence references, claim-level ground truth, materiality/severity labels, annotation provenance/dispute resolution, train/held-out split, dataset version, and raw-count formulas for critical-error recall, false-positive rate, claim classification, completeness, latency, inference cost, reviewer workload, omission recall, and false-warning rate. **Requirements:** FR-14.8. **Depends on:** T019.
- [ ] T022 Add content-minimized telemetry and tests for source/note/resident version IDs, policy/ruleset/dataset/model/prompt versions, status counts, denominator, linked finding counts, persisted execution metrics, latency, retries, input/output tokens, inference cost, rejection/warning counts, and safe failures; verify no full transcript/note logging. **Requirements:** FR-14.5, FR-14.8. **Depends on:** T016.
- [ ] T023 Run configured format/static checks, focused/new tests, complete test suite, compile check, and `git diff --check`; record exact commands/results. **Requirements:** definition of done. **Depends on:** T020-T022.
- [ ] T024 Have an independent reviewer update the reviewer-owned checklist; the implementation workflow must not modify it. **Depends on:** T023.
- [ ] T025 Run [converge.md](converge.md), append only concrete new gap tasks if needed, implement those tasks, and repeat until convergence reports `Converged`. **Depends on:** T024.

## Dependency summary

```text
T001 -> T002 -> T003 -> T004/T005/T008
T005 -> T006 -> T007
T003 + T006 -> T009 -> T010 -> T011 -> T019
T003 -> T008 -> T012 -> T013
T007 + T010 + T012 + T013 -> T014 -> T015/T016/T018
T016 -> T017
T017 + T019 -> T020 -> T023 -> T024 -> T025
T019 -> T021; T016 -> T022; T020-T022 -> T023
```

