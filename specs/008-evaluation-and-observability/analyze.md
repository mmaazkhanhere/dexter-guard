# Spec 008 Read-Only Consistency Analysis

**Analysis date:** 2026-10-13  
**Reviewed:** spec.md, specify.md, clarify.md, data-model.md, contracts/evaluation.openapi.yaml, plan.md, checklist.md, tasks.md; constitution, architecture, existing Specs 001–007, and project stack.

## Result

**Internally consistent with implementation evidence, subject to independent checklist review.** The documents maintain upstream ownership: Specs 003–006 produce pipeline outputs, Spec 007 owns review/approval, and Spec 008 measures immutable results. The headless runner remains independent of React.

## Confirmed alignment

| Area | Evidence |
| --- | --- |
| FR-26–FR-33 coverage | Each is specified in spec.md, mapped in tasks.md, and testable through EVAL scenarios. |
| Required metrics | Exact supplied definitions, raw counts, failure/zero handling, and uncertainty appear in spec.md and are represented in data-model.md. |
| Held-out protection | Explicit split/family/hash validation and no-tuning rule in spec, clarification, model, plan, and T003–T005/T021. |
| Matching integrity | Target-aware one-to-one matching, duplicate/partial handling, and status semantics align across spec/model/plan/T009. |
| Baseline pairing | Same candidate hash requirement and baseline finding exclusion align across spec/model/plan/T011. |
| Observability | Immutable configuration, stage timing/cost, safe telemetry, and historical/live labels align across spec/model/plan/tasks. |
| Invariants/scope | Evidence integrity, synthetic-only restriction, and exclusions are retained; no engine duplication or clinical claim is introduced. |

## Remaining implementation gates

1. The accepted executable fixture is deterministic and synthetic-only. Provider pricing/token state is not available for saved fixtures, so cost is reported `UNAVAILABLE` rather than fabricated.
2. Existing concrete pipeline ports are not composed by a shared application factory in this checkout. Spec 008 uses a reference-only adapter protocol and saved fixture adapter; no upstream reliability logic is duplicated.
3. The report/dashboard implementation is a lightweight FastAPI/JSON diagnostic surface. No React host exists in the checkout, so no frontend dependency was introduced.
4. The prior checklist approval is superseded by the amended contract/lifecycle artifacts; the amendment review criteria CQ-008-25 through CQ-008-29 require independent re-review. This does not claim that implementation, the accepted benchmark, or convergence evidence exists.

The prior constitution-consistency gaps are resolved in the source artifacts. Resident-context mixing is now optional extension coverage only; the `008-evaluation.md` naming is mapped to the canonical `spec.md`; and `sourceVersion`/`noteRevision` are typed as positive integers in the data model.

The API contract now uses explicit schemas for run configuration, case results, findings/matches, comparisons, and typed metric families. Live synthetic demonstrations are tracked through immutable upstream references, not a duplicate ingestion/generation workflow. The local API is explicitly synchronous and returns terminal runs; terminal results are immutable.

No source ambiguity was resolved by inventing a contract. Implementation evidence is recorded in `converge.md`; re-run this analysis after any clarification, plan, task, or contract change and before independent review.

