# Spec 005 — Implementation Procedure

## Gate

Before any implementation task, read [checklist.md](checklist.md). If any item is unchecked, stop and ask the designated reviewer to complete its requirements-quality review. Do **not** change checklist markers. This gate applies even if implementation tasks look straightforward.

## Procedure

1. Read the constitution, [spec.md](spec.md), [clarify.md](clarify.md), [data-model.md](data-model.md), [plan.md](plan.md), [ADR 004](../../docs/adr/004-deterministic-validation-boundary.md), and [tasks.md](tasks.md).
2. Execute open tasks strictly in dependency order. Begin with T001; do not infer upstream contracts or create a parallel backend layout.
3. Before each implementation slice, write the task's contract/unit/acceptance test. Use synthetic data only.
4. Keep the rule engine pure: no LLM client, network call, semantic retrieval, clinical threshold, or approval logic may be imported into rule evaluation.
5. Treat `NOT_EVALUABLE` as a retained non-pass and preserve any independent evidence-integrity failure. Never convert a malformed, ambiguous, or unavailable comparison into a pass.
6. Run the full verification set specified in T025 after all dependent tasks. Update task checkboxes only for completed implementation work with verification evidence; never update `checklist.md`.
7. Complete T026 only through a human reviewer and then run the convergence procedure.

## Required implementation invariants

- Exact `Decimal` arithmetic, documented conversion matrix, and fixed result ordering.
- Explicit upstream alignment is mandatory before numeric comparison.
- Exact Spec 001 source/version and Unicode code-point span/quotation validation.
- Finding traceability through rule/ruleset version, source fact ID, claim ID, and alignment ID.
- Spec 007 receives findings but owns final severity/approval policy; Spec 008 receives rules/fixtures but owns evaluation thresholds.

