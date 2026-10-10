# Cross-Artifact Consistency Analysis — Spec 003

**Mode:** Read-only requirements analysis  
**Artifacts reviewed:** `spec.md`, `data-model.md`, `clarify.md`, `plan.md`, `tasks.md`  
**Result:** No unresolved internal conflicts, constitutional violations, or planning gaps remain after the remediation pass recorded below.

## Consistency findings

| Area | Result | Evidence |
|---|---|---|
| Feature boundary | Consistent | All artifacts limit work to candidate-note claim extraction and exclude evidence verification/diagnosis. |
| FR-06 | Covered | `spec.md` requires atomic, addressable claims; T004–T006 define tests/fixtures, T008–T012 implement them, and T015 executes acceptance coverage. |
| Negation/certainty/attribution | Covered | Contract and semantic rules are mirrored by T004–T006, validator T010, and acceptance T015. |
| Numeric fidelity | Covered | Raw representation, decimal normalization, units, approximation, and validation invariants agree across artifacts. |
| Span/revision integrity | Covered | Exact dual-coordinate spans and immutable revision ownership are specified, planned, and assigned in T002/T005/T009/T010/T012. |
| Empty versus failure | Consistent | `EMPTY` is a valid no-assertion outcome; malformed/invalid output is all-or-nothing `FAILED`. |
| Optional endpoint | Consistent | A mandatory service interface is planned; HTTP adapter task T009 remains conditional. |
| Acceptance coverage | Covered | CLM-001 through CLM-016 are specified in `spec.md`, prepared in T006, and executed in T015. |
| Security | Covered | Protected logging is a requirement, architecture constraint, and T016 validation task. |
| Constitution stack | Covered | The plan requires Python, FastAPI, Pydantic, SQLite, dependency injection, and ADRs for material design trade-offs. |
| Synthetic-only/privacy | Covered | NFR-003-04, clarification decision, plan constraints, T002/T013/T016, and the checklist prohibit real data. |
| Provenance/evidence handoff | Covered | Body hash, single resident test ID, immutable evidence-source reference, extraction run id, append-only history, and provider/model/prompt/schema versions are defined and tasked. |
| Test-first/evaluation | Covered | T004–T007 precede T008–T012, and the plan/T006/T017 require 100+ versioned synthetic scenarios with required corpus fields, metrics, denominators, and a held-out policy. |
| Operational failures/security | Covered | Typed discriminated failures, provider timeout/bounded retry, idempotent run ids, input-size guard, secret/dependency checks, and redacted metrics are specified and tested. |

## Deliberate non-decisions that are safe

- The actual provider (LLM/model/vendor) is behind a port. This is intentional because the feature contract and validation behavior must not depend on it.
- The optional HTTP endpoint may be omitted. Pydantic is always required; if HTTP is exposed, the versioned FastAPI/OpenAPI contract is mandatory.
- Exact HTTP status codes defer to repository conventions; result-state and no-partial-claims semantics do not.

## Review outcome

The reviewer-owned checklist is intentionally not marked by this analysis. Its remaining unchecked state is a process gate for implementation, not a requirements inconsistency. Re-run this analysis after implementation tasks change the design or after a reviewer identifies a checklist issue.

## Implementation consistency notes

- The user request named `specs/003-claim-and-source-fact-extraction`, but the
  repository's approved feature path is `specs/003-claim-extraction`; the latter
  is used without renaming artifacts.
- The repository is already on branch `spec-003`. The appended Spec 002 branch
  and commit-scope instruction was not applied because it is materially
  unrelated to this feature.
- `spec.md`/`data-model.md` define a closed `ExtractionErrorCode` enum while an
  earlier plan sentence names `EMPTY_RESULT_UNCERTAIN`; no new enum value was
  added. The bounded empty-result safeguard returns
  `INTERNAL_VALIDATION_ERROR` when it detects a possible assertion.
- `implement.md` mentions a mandatory handoff event, while the normative data
  model explicitly rejects asynchronous delivery/outbox scope. Typed persisted
  results and `get_current_result()` are the handoff mechanism.
- Specs 004, 006, and 008 currently contain no contracts in this repository.
  Spec 003 therefore provides the typed handoff and feature-level synthetic
  fixture/metric functions, but cannot validate a downstream verifier or
  register a shared benchmark threshold that does not yet exist.

## Constitution re-check

The remediation pass resolved five prior issues: mandatory evidence-verification handoff, a discriminated typed-failure contract, a genuinely test-first task graph, complete evaluation-corpus/metric requirements, and synchronized CLM-001–CLM-016 references. The re-check confirms that Spec 003 does not weaken the human-approval invariant, uses only synthetic data, and limits its own role to claim extraction while requiring a durable handoff to Spec 004 for transcript evidence. No ADR is required for the documented architecture; an ADR remains required if implementation materially departs from it.
