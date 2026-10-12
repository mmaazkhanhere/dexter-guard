# Spec 004 — Convergence Procedure

**Purpose:** Verify the codebase against spec.md, clarify.md, annotation-policy.md, contracts/verification-runs.openapi.yaml, plan.md, and tasks.md after implementation. This procedure is read-only except that it may append newly discovered implementation tasks to tasks.md. It never changes checklist.md.

## Preconditions

- A reviewer has completed the requirements-quality checklist.
- Implementation tasks through the intended scope have been attempted.
- The repository’s normal test, type-check, lint, and migration commands are available.

## Verification sequence

1. Re-read the specification, clarification record, annotation policy, executable OpenAPI contract, technical plan, and task list.
2. Inspect implementation code, route registration, schemas, persistence/migrations, configuration, logs/metrics, fixtures, and tests against the repository architecture.
3. Build a traceability matrix from every functional requirement, acceptance scenario, contract field, lifecycle state, and safety rule to executable code and a passing test.
4. Confirm source-only evidence: no path allows candidate-note text, other claims, retrieval score, or prior run to ground a result.
5. Confirm all successful runs have complete, unique claim coverage and one status per claim.
6. Confirm SourceSpan uses the defined Unicode code-point range and source-derived quotation; exercise corrupted offsets and quotation mismatch.
7. Confirm failure isolation: stale provenance, invalid span, malformed/unknown model response, timeout, and persistence failure cannot result in SUCCEEDED or authoritative partial findings.
8. Confirm qualifier treatment against EV-004 through EV-007 and EV-013 against `EVIDENCE_ANNOTATION-v1`, including certainty, attribution, and partial-negation outcomes.
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

**Status: Implementation evidence complete; reviewer gate pending.** The
runtime, contract, fixture, end-to-end, telemetry, operations, and evaluation
handoff evidence is now present and the executable Spec 004 suite passes. The
branch is not yet `Converged` because checklist.md is reviewer-owned and its
integration-test markers and final review decision remain open. T030 and T031
must be completed by the designated reviewer/convergence run; this procedure
must not self-approve those markers.

Latest implementation evidence:

- `uv run pytest tests/evidence_verification -q`: 62 passed.
- `uv run python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- EV-001 through EV-014 manifest, immutable-fixture API acceptance, safe
  failure cases, content-free telemetry, operations runbook, and Spec 008
  handoff are versioned in the referenced artifacts.
