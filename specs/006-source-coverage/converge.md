# Spec 006 - Convergence Procedure

## Goal

Verify that implemented code completely satisfies Spec 006's specification, clarification decisions, model/contract, plan, and tasks. This procedure is read-only except it may append concrete gap tasks to [tasks.md](tasks.md). It never edits [checklist.md](checklist.md).

## Review sequence

1. Confirm independent checklist approval and task evidence.
2. Compare public Pydantic/API models with `COVERAGE-CONTRACT-v1`, ADR 005, and [compatibility-review.md](compatibility-review.md), including reference-only request validation, resident trust context, source hash/normalization, required ruleset/dataset/model/prompt metadata, idempotency/retry semantics, success/failure exclusivity, source-span semantics, and absence of approval/mutation fields.
3. Trace FR-14.1 through FR-14.8 and every COV scenario to implementation and a passing test.
4. Inspect extraction to prove each asserted source fact has valid immutable spans, atomic attributes, documented expectation, source-derived quotation, and no uncited invented fact; inspect unresolved-item handling separately.
5. Inspect matching/status precedence using faithful paraphrase, laterality, negation, uncertainty, attribution, temporal modifier, approximation, care action, mobility, and incompatible value fixtures.
6. Confirm successful run closure: every expected fact/unresolved item exactly once, contextual facts excluded, only `COVERED` in numerator, zero denominator `null`, and runtime count basis explicitly labelled.
7. Confirm correlation references preserve (rather than replace) Spec 004/005 outcomes and Spec 007 remains final severity/approval owner. If Spec 007/008 contracts are unavailable, report convergence as conditional rather than complete.
8. Confirm new note revisions create new immutable coverage runs and no code auto-resolves old findings.
9. Re-run COV-001 through COV-011, contract/unit/integration/property tests, full test suite, compile/static/format checks configured by the project, telemetry cost/token assertions, idempotency/retry tests, and `git diff --check`.
10. Review the Spec 008 handoff to ensure held-out completeness uses manual annotated facts and reports raw counts, omission recall, false-warning rate, and split protection.

## Outcome rules

- **Converged:** Every requirement, invariant, and acceptance case maps to implementation and passing evidence; tasks are complete; no constitutional violation, contract drift, or unchecked reviewer gate remains.
- **Gaps found:** Append one unchecked, dependency-ordered task per gap stating the missing requirement, code/test evidence, dependency, and acceptance proof. Then run `implement.md` for new tasks and repeat this procedure.
- A missing source citation, fabricated source fact, unsafe partial success, automatic note change/approval, severity decision by Spec 006, system-only benchmark completeness, or failed/unavailable test is **not converged**.

