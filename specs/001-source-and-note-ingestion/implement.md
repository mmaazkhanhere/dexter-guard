# Implementation Workflow: Source Transcript Ingestion and Evidence Reference Foundation

## Purpose

Execute the actionable tasks in `tasks.md` in dependency order after the requirements and design artifacts have passed clarification, checklist review, and consistency analysis.

This file defines the implementation workflow. Creating this file does not authorize or perform application-code implementation.

## Invocation

```text
/speckit.implement [phase, user story, or task range]
```

Examples:

```text
/speckit.implement
/speckit.implement Phase 2 foundational
/speckit.implement User Story 1
```

## Required inputs

Read in this order:

1. `.specify/memory/constitution.md`
2. `specs/001-source-and-note-ingestion/spec.md`
3. `specs/001-source-and-note-ingestion/plan.md`
4. `specs/001-source-and-note-ingestion/data-model.md`
5. `specs/001-source-and-note-ingestion/contracts/source-api.yaml`
6. `specs/001-source-and-note-ingestion/tasks.md`
7. Every file referenced by the selected tasks

## Checklist gate

Before executing any task:

1. Scan `specs/001-source-and-note-ingestion/checklist.md` and any checklist files under `specs/001-source-and-note-ingestion/checklists/`.
2. Count checked and unchecked reviewer-owned items.
3. Do not modify checklist files or checkbox markers.
4. If any custom checklist item is unchecked, report the count and ask the reviewer whether to proceed.
5. Treat checked items as requirements-quality approval only; they do not represent completed implementation work.
6. Do not proceed if `analyze.md` has not reported `CLEAN`, unless the reviewer explicitly overrides the gate.

## Execution rules

- Execute Phase 1 Setup before Phase 2 Foundational.
- Complete foundational tasks before any user-story task.
- Execute user stories in the dependency order declared in `tasks.md`.
- Execute `[P]` tasks in parallel only when they touch different files and have no unfinished dependency.
- Execute test tasks before the implementation tasks they validate when the task phase specifies that order.
- Preserve the exact source-text, source-version, Unicode-span, atomicity, and scope invariants in `spec.md`.
- Do not add audio, speech recognition, resident disambiguation, clinical reasoning, production authentication, or external nursing-note ingestion.
- Do not introduce an LLM dependency into validation, persistence, or evidence-span tests.
- Mark a task complete only after its implementation and relevant verification succeed.
- If an implementation discovery changes requirements, stop and update `spec.md` through clarification before changing derived artifacts.

## Phase checkpoints

### Setup

Confirm the runtime, package layout, test runner, and persistence conventions. If the paths in `tasks.md` are wrong, stop and revise `plan.md` and `tasks.md` before implementation.

### Foundational

Confirm source contracts, structured errors, repository operations, and API schema validation are available before user stories begin.

### User Story 1

Verify valid source submission, exact text round-trip, unique source ID, version 1, structured input validation, and no partial persistence.

### User Story 2

Verify immutable historical retrieval, atomic expected-version checks, uniqueness protection, and deterministic stale/concurrent conflict handling.

### User Story 3

Verify Unicode scalar-value span semantics, exact version binding, valid resolution, and rejection of invalid boundaries or missing references.

### Polish

Run the complete feature test suite, verify contract/data-model/task consistency, and confirm excluded capabilities were not introduced.

## Completion report

Report:

- tasks completed and remaining;
- files changed;
- tests run and results;
- checklist checked/unchecked counts, without changing markers;
- any deviations from the plan;
- whether `converge.md` should run next.

Implementation is not complete merely because all tasks were attempted. The feature must pass its acceptance tests and then be verified by `converge.md`.
