# Spec 006 - Consistency Analysis

**Analysis type:** Read-only cross-artifact review  
**Artifacts reviewed:** `specify.md`, `spec.md`, `clarify.md`, `data-model.md`, `contracts/coverage-runs.openapi.yaml`, `plan.md`, `tasks.md`, [ADR 005](../../docs/adr/005-source-coverage-boundary.md), [compatibility-review.md](compatibility-review.md), the constitution, architecture, and adjacent Specs 004-005.

## Result

The internal Spec 006 artifacts are consistent after the precedence, unresolved-item, and contract-alignment revisions. The requirements-quality checklist has been reviewed and approved with all 21 items checked. Repository compatibility is verified for Specs 001-005 in [compatibility-review.md](compatibility-review.md), but Specs 007 and 008 are not present in this repository; downstream compatibility remains an explicit pre-implementation gate.

## Requirement traceability

| Requirement | Specification | Planned control | Tasks |
| --- | --- | --- |
| FR-14.1 source facts/spans | US-1; data contracts | extraction port, span validator, immutable repository | T005-T008, T015, T019-T020 |
| FR-14.2 attributes/importance | US-1; expected-fact policy | typed attributes and pure policy mapper | T005-T007, T011 |
| FR-14.3 semantic matching | US-2; matching policy | structured matcher port and relation validator | T009-T011, T014 |
| FR-14.4 classification | US-3; status precedence | pure relation-to-status orchestration | T010-T011, T020 |
| FR-14.5 findings | US-3/US-4; finding contract | derived quotes, safe suggestion, no mutation | T008, T012, T016-T017 |
| FR-14.6 linked findings | US-3; related references | correlation adapter only | T013, T020 |
| FR-14.7 revision re-evaluation | US-4 | immutable run binding/revision integration | T014, T018, T020 |
| FR-14.8 honest metrics | US-5; data model | labelled runtime counts and Spec 008 handoff | T004, T014, T019-T022 |

## Consistency checks

| Check | Result | Evidence |
| --- | --- | --- |
| Exactly one coverage outcome per assessed expected fact/item | Pass | Status policy, data-model invariants, plan orchestration, T010/T015/T020. |
| Operational failure distinct from `UNCERTAIN` | Pass | CL-010/CL-013, API contract, plan failure policy, T009/T015/T017. |
| Source-only authority and valid span rules | Pass | Scope, CL-002/CL-005, model invariants, span tasks. |
| Material qualifier preservation | Pass | CL-007, US-1/US-2, matcher design, T005/T011. |
| Contextual details do not inflate denominator | Pass | expected-fact policy, data model counts, T007/T020. |
| Runtime metric cannot masquerade as benchmark completeness | Pass | US-5, CL-015, `metricBasis`, T021. |
| Severity ownership remains Spec 007 | Pass | policy table, CL-004, plan components, T007/T013. |
| Numeric/contradiction ownership remains Specs 005/004 | Pass | scope, CL-011/CL-012, correlation-only plan/task. |
| Revisions preserve history | Pass | US-4, CL-016, plan persistence, T018. |
| All COV cases testable | Pass | acceptance table and T019/T020 provide exact assertions. |
| Faithful coverage outranks contradictory duplicate | Pass | CL-008/CL-009, explicit pseudocode and COV-011, plan first-match table, T011/T020. |
| Unresolved source items remain review-required | Pass | CL-010/CL-015, `unresolvedSourceItemsRequireReview`, runtime-count text, T019/T020. |
| Run metadata satisfies constitution | Pass | Required resident context, source hash/normalization, ruleset/dataset/model/prompt versions, correlation, and idempotency are in the model, OpenAPI contract, ADR 005, and T003/T014/T022. |
| Retry and idempotency are fail-safe | Pass | CL-017/018, mandatory request key, 30-second/two-attempt bound, same-digest replay, and conflict behavior are specified. |
| Evaluation and observability handoff is complete | Pass | Source text, claim-level outcomes, annotation provenance, materiality/severity labels, all constitution metrics, and content-minimized cost/token telemetry are assigned to T019-T022. |
| Cross-component architecture is documented | Pass | ADR 005 records alternatives, consequences, provider boundary, and change-control version. |
| Adjacent contract compatibility | Conditional | Specs 001-005 verified in `compatibility-review.md`; Spec 007/008 artifacts are absent and must be supplied before those integrations are implemented. |

## Controlled implementation decisions

Provider selection, prompt text, router placement, and SQLite migration mechanics are intentionally assigned to repository conventions in T001. Timeout/retry values, idempotency, source normalization, run metadata, source authority, status precedence, immutable revision binding, no-auto-edit, policy ownership, and metric definitions are normative and may not be weakened by implementation choices.

## Checklist gate

All 21 custom checklist items are checked. Implementation may proceed through T001/T002, but T002 must keep the Spec 007/008 compatibility gate open until those contracts are supplied and reviewed.

