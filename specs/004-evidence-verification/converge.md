# Spec 004 — Convergence Procedure

**Purpose:** Verify the codebase against specify.md, clarify.md, plan.md, and tasks.md after implementation. This procedure is read-only except that it may append newly discovered implementation tasks to tasks.md. It never changes checklist.md.

## Preconditions

- A reviewer has completed the requirements-quality checklist.
- Implementation tasks through the intended scope have been attempted.
- The repository’s normal test, type-check, lint, and migration commands are available.

## Verification sequence

1. Re-read the specification, clarification record, technical plan, and task list.
2. Inspect implementation code, route registration, schemas, persistence/migrations, configuration, logs/metrics, fixtures, and tests against the repository architecture.
3. Build a traceability matrix from every functional requirement, acceptance scenario, contract field, lifecycle state, and safety rule to executable code and a passing test.
4. Confirm source-only evidence: no path allows candidate-note text, other claims, retrieval score, or prior run to ground a result.
5. Confirm all successful runs have complete, unique claim coverage and one status per claim.
6. Confirm SourceSpan uses the defined Unicode code-point range and source-derived quotation; exercise corrupted offsets and quotation mismatch.
7. Confirm failure isolation: stale provenance, invalid span, malformed/unknown model response, timeout, and persistence failure cannot result in SUCCEEDED or authoritative partial findings.
8. Confirm qualifier treatment against EV-004 through EV-007 and EV-013, including CERTAINTY-v1 decision boundaries.
9. Confirm Spec 004 has not absorbed Spec 005–008 responsibilities.
10. Run all required automated checks and inspect their reports.

## Convergence result format

Record one of these results:

### Converged

Use only when every requirement maps to implemented behavior and a passing test, all safety invariants are demonstrated, all planned tasks are complete or deliberately superseded with rationale, and no new work is necessary.

### Gaps found

For each gap, append a new unchecked task to tasks.md with:

- unique task ID;
- precise missing behavior or test;
- source requirement or scenario;
- dependency;
- acceptance evidence.

Then run implement.md for those new tasks and re-run this convergence procedure. Do not mark custom checklist items as part of the process.

## Current baseline

**Status: Documentation complete; code convergence not yet runnable.** This document set defines the convergence criteria, but Spec 004 implementation tasks remain unchecked and no code/test evidence has been supplied. It would be inaccurate to report “Converged” before implementation, reviewer approval, and T029–T031.
