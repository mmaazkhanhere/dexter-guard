# Spec 008 Implementation Procedure

## Purpose

Execute [tasks.md](tasks.md) in dependency order after the specification gate is approved. This procedure is an implementation guide; it does not claim that any task, test, benchmark, or threshold has passed.

## Mandatory preflight gate

1. Read the current [checklist.md](checklist.md) in full.
2. If any reviewer-owned item is unchecked, stop before modifying code or fixtures and ask the user/reviewer whether to proceed despite the unchecked gate. Do not alter checklist text, checkbox state, reviewer identity, date, decision, or exceptions.
3. Read spec.md, clarify.md, data-model.md, contracts/evaluation.openapi.yaml, plan.md, tasks.md, and analyze.md.
4. Confirm the reviewed repository revision and the actual ports/contracts of Specs 001–007. If they differ from the planning assumptions, document the gap and return to clarification/planning rather than silently adapting requirements.
5. Confirm only synthetic data is in scope. Do not use real healthcare content in fixtures, logs, screenshots, manual tests, or provider calls.

## Execution order

1. Complete T001–T005: compatibility discovery, annotation guidance, dataset authoring/review, and accepted benchmark validation.
2. Complete T006–T008: contracts, append-only persistence, and content-minimised configuration/telemetry.
3. Complete T009–T012 with deterministic unit tests before runner orchestration.
4. Complete T013–T016: reference-only adapters, headless runner, failure behavior, and deterministic/live execution entry points.
5. Complete T017–T019: query/export/reporting and saved-vs-live display states.
6. Complete T020–T023: full acceptance, protected regression gate, evidence record, re-analysis, convergence, and independent re-review.

Do not reorder around an unmet dependency. Mark a task complete only after its stated implementation and task-specific test evidence are present. A passing broad test suite is not proof that an individual task is complete.

## Implementation constraints

- Reuse source IDs/versions, note IDs/revisions, claim IDs, evidence statuses, source spans, ruleset versions, and review artifacts from their owner specifications.
- Do not make the React client a dependency of the runner or CI.
- Do not reimplement claim extraction, semantic verification, deterministic rules, coverage, or approval policy.
- Keep evaluation runs/dataset versions append-only. A re-run always receives a new evaluation-run ID.
- Validate data/split integrity before invoking a model. Preserve typed partial results and failures.
- Keep held-out data out of tuning/model-selection flows. The only approved numerical gate is held-out critical-error recall >=95%; other observed deltas require review, not invented pass/fail thresholds.
- Log only safe IDs, hashes, versions, counts, duration, token/cost metadata, and error codes. Never log source/note/prompt/raw output content or secrets.
- Do not claim clinical safety, caregiver-performance improvement, or medical truth from benchmark results.

## Required evidence after each phase

Record command, UTC timestamp, git revision, selected dataset/configuration, exit status, test count, and safe result summary. Use the project's standard formatter/static/pytest commands plus the deterministic headless benchmark command. Live model evaluations must record provider/model/prompt/inference/pricing configuration and may not replace deterministic test evidence.

## Completion handoff

After all tasks have task-specific evidence, update the read-only analysis, run the convergence procedure, and request independent checklist review. If convergence identifies a code/test gap, append one actionable unchecked task to tasks.md, implement it, and converge again.

