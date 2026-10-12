# Spec 007 — Convergence Procedure

## Goal

Verify that the implemented codebase completely satisfies Feature 007's specification,
clarifications, data model, contracts, plan, and dependency-ordered tasks. This procedure is
read-only except that it may append narrowly scoped implementation tasks to
[`tasks.md`](tasks.md). It must never silently mark reviewer-owned checklist items complete.

## Tooling status

No installed `specify`, `speckit`, `/speckit-implement`, or convergence command was found in the
available repository/tool environment. This document records the required workflow and does
not simulate command execution. When the project toolchain is available, run the implementation
stage only after the independent checklist gate, then repeat this convergence procedure.

## Review sequence

1. Confirm independent requirements-quality approval and task evidence. The architecture
   self-review is not a substitute for that gate.
2. Compare the implemented Pydantic/OpenAPI models and API behavior with
   [`contracts/review-audit.openapi.yaml`](contracts/review-audit.openapi.yaml), including
   terminal verification states, exact source/note/run bindings, expected-revision conflicts,
   conditional suggestion fields, and the common error envelope.
3. Verify the concrete Specs 001–006 ports, repositories, versions, timeout/retry rules,
   idempotency behavior, migrations, and fixtures using
   [`compatibility-review.md`](compatibility-review.md). Missing evidence is a dependency gap,
   not permission to infer an interface.
4. Trace FR-15 and FR-17–FR-25, HR-001–HR-018, and each `[US#]` task mapping to implementation
   and passing tests. Confirm no component task bypasses the user-story outcome or ownership
   boundary.
5. Inspect source-span validation and highlighting for exact immutable source versions,
   Unicode code-point semantics, missing/invalid evidence states, and candidate/source
   separation.
6. Verify immutable revisions, compare-and-append concurrency, stale finding/run behavior,
   final-disposition immutability, and append-only audit history.
7. Verify claim-level re-verification cannot authorize approval and that final full-note
   verification contains the exact current claim set plus complete successful 004/005/006
   component results.
8. Exercise backend approval guards for stale, failed, malformed, incomplete,
   source-mismatched, unresolved-critical, and unresolved-source-item cases. Confirm rejection
   remains possible after verification failure and approval is atomic against concurrent edits.
9. Run contract, unit, repository, API, UI, acceptance, static/compile, observability,
   idempotency/retry, and `git diff --check` checks configured by the implementation repository.
10. Verify the [Spec 008 evaluation handoff](../../docs/evaluation/spec007-handoff.md), including
    the required versioned 100+ synthetic German benchmark, held-out metrics, thresholds, and
    model/prompt/ruleset/dataset provenance. Do not claim clinical safety or improvement from
    feature acceptance tests alone.
11. Confirm [ADR 006](../../docs/adr/006-human-review-and-audit-boundary.md) still matches the
    verified upstream interfaces and transaction boundary.

## Outcome rules

- **Converged:** Every applicable requirement, invariant, acceptance scenario, contract,
  dependency, and task has implementation evidence and passing tests; no unchecked
  implementation task, unresolved compatibility gate, unchecked reviewer gate, contract drift,
  or constitutional violation remains.
- **Gaps found:** Append one unchecked, dependency-ordered task to `tasks.md` for each concrete
  gap, including requirement/user-story ID, evidence, dependency, target, and acceptance proof.
  Run the available implementation command for those tasks, then repeat this procedure.
- A missing upstream contract, unavailable test, fabricated evidence, unsafe partial success,
  automatic correction/approval, overwritten history, or failed approval guard is **not
  converged**.

## Historical documentation baseline — 2026-10-12

**Superseded baseline — planning-only state.** At the time this baseline was written, Spec 007 application implementation had not started,
the independent requirements-quality checklist gate remains pending, concrete Specs 001–006
implementation compatibility is not established in the available archive, and the Spec 008
benchmark has not been executed. These gaps are already represented by T001–T004, T021–T034,
T035, and T036; no duplicate gap tasks are appended by this documentation-only review.

The documentation package is ready for independent review and subsequent implementation. After
implementation and test evidence exist, rerun this procedure until the result can truthfully
be reported as **Converged**.

## Latest repository verification — 2026-10-12

The repository now contains a partial Spec 007 implementation. Verification evidence:

- `pytest -q tests/human_review`: 19 passed.
- `.venv\Scripts\python.exe -m pytest -q`: full repository suite passed.
- `.venv\Scripts\python.exe -m compileall -q src tests`: passed.
- `git diff --check`: passed.

The result remains **Not converged — implementation gaps found**. The following concrete gaps
were identified by comparing the implementation with the contract and task artifacts:

1. The documented `/full-verifications` endpoint is absent from `src/human_review/api.py`.
2. Structured suggestion acceptance/rejection is not exposed through the API, and the decision
   route does not persist `suggestionId` or enforce the accepted-successor contract.
3. Approval checks do not yet enforce every documented predicate, including required decision
   completeness, exact component-run/source/claim-set closure, and unresolved Spec 006 source
   item blocking.
4. SQLite persistence currently covers audit events, not the complete review-owned entity set.
5. Contract, UI, end-to-end acceptance, idempotency-digest, retry, and observability coverage is
   incomplete; the remaining unchecked tasks are not implementation evidence.

These gaps are represented by newly appended tasks T037–T042 in `tasks.md`. No duplicate tasks
were added for gaps already covered by earlier tasks. Convergence must be rerun after those
tasks are implemented and tested; the feature is not ready to report as **Converged** or proceed
to an implementation PR.

## Latest implementation correction review — 2026-10-12

The following convergence gaps were corrected:

- Added the `/full-verifications` API route and terminal aggregate orchestration.
- Added explicit suggestion acceptance/rejection decision handling with successor revision
  linkage and idempotency binding.
- Strengthened approval checks for exact component-run references, source binding, decision
  completeness, and unresolved coverage items.
- Added durable SQLite persistence for notes, findings, decisions, suggestions, verification
  aggregates, dispositions, idempotency records, and audit events.
- Added regression coverage for full verification and accepted suggestions.

Verification after the corrections passed the focused Spec 007 suite, the full repository
suite, compilation, and `git diff --check`.

The result is still **Not converged**. The implementation corrections above are regression
evidence, but they do not by themselves satisfy the completion conditions in `tasks.md`.
The task ledger currently leaves T003–T042 unchecked. In particular:

- T003–T036 still require their fixture, contract, frontend, integration, acceptance,
  observability, ADR, and evaluation completion evidence.
- T037–T040 describe behavior that is present in the current partial implementation, but their
  required task-specific tests and completion evidence have not been recorded, so they remain
  open rather than being inferred complete from the focused suite.
- T041–T042 remain incomplete: the repository has no React/frontend implementation or complete
  contract/acceptance/observability coverage for every documented route, and the Spec 008
  benchmark/release evidence has not been executed.

This reconciles the convergence result with the task ledger: passing tests demonstrate partial
behavioral correctness, not task completion. The remaining tasks must be completed and checked,
then this procedure rerun before reporting **Converged** or opening an implementation PR.
