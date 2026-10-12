# Spec 005 — Convergence Procedure

## Goal

Verify that the implemented codebase completely satisfies Spec 005's specification, design, and task artifacts. This procedure is read-only except that it may append newly discovered, narrowly scoped implementation tasks to [tasks.md](tasks.md). It must never mark reviewer-owned checklist items.

## Review sequence

1. Confirm the checklist gate was completed by a reviewer and all completed tasks have evidence.
2. Compare implemented public models/API to [contracts/deterministic-validation.openapi.yaml](contracts/deterministic-validation.openapi.yaml) and `DVE-CONTRACT-v1`.
3. Trace every `NUM-*`, `STR-*`, and `EVD-*` catalog rule to implementation, a focused test, and one acceptance fixture where applicable.
4. Re-run AT-001 through AT-021 and inspect exact rule IDs, outcome, references, canonical values/units, structural/schema behavior, complete run metadata, API errors, repeated-pair behavior, and no-finding valid-equivalence behavior.
5. Inspect imports/mocks/runtime telemetry to prove rule execution makes no LLM or network call and does not perform semantic alignment.
6. Inspect source/version/span/quotation validation and ensure no Unicode offset normalization or stale-source fallback occurs.
7. Check deterministic repeatability, result ordering, Decimal serialization, immutability/provenance, minimized logging, and Spec 007/008 handoffs.
8. Run the repository's formatter, static checks, unit, contract, integration, acceptance, and `git diff --check` verification.

## Outcome rules

- **Converged:** Every requirement and acceptance scenario has implementation and passing evidence; no unchecked implementation task, contract drift, test gap, or constitutional violation remains.
- **Not converged:** Append one dependency-ordered task per concrete gap to `tasks.md`, including requirement ID, evidence, and test needed. Run `implement.md` for those tasks, then rerun this procedure.
- A failing or unavailable test, an unapproved custom checklist, a semantic-comparison dependency, an LLM call, or an untraceable evidence reference is **not converged**.

