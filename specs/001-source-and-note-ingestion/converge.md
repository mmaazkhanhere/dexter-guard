# Convergence Workflow: Source Transcript Ingestion and Evidence Reference Foundation

## Purpose

Verify the current codebase against the feature's specification, plan, tasks, constitution, data model, and API contract after implementation. Determine whether the feature is complete, and append any remaining implementation work to `tasks.md` so `implement.md` can execute it.

This workflow is a post-implementation completeness check. It does not rewrite the specification, plan, checklist, or existing tasks.

## Invocation

```text
/speckit.converge [focus area]
```

Run it only after `implement.md` has executed the current `tasks.md` and after `tasks.md` was generated or regenerated from the current design artifacts.

## Inputs

Read:

1. `.specify/memory/constitution.md`
2. `specs/001-source-and-note-ingestion/spec.md`
3. `specs/001-source-and-note-ingestion/plan.md`
4. `specs/001-source-and-note-ingestion/tasks.md`
5. `specs/001-source-and-note-ingestion/data-model.md`
6. `specs/001-source-and-note-ingestion/contracts/source-api.yaml`
7. `specs/001-source-and-note-ingestion/checklist.md` for status only
8. The relevant implemented source, test, and configuration files

Treat `spec.md` and the constitution as the governing intent. Do not use git history or branch comparison as a substitute for checking current behavior.

## Verification scope

Verify:

- every P1 user story and acceptance scenario;
- FR-01 and all other functional requirements;
- exact source-text preservation;
- unique source IDs and version 1 creation;
- immutable historical versions;
- atomic expected-version revision writes;
- `VERSION_CONFLICT` behavior for stale or concurrent revisions;
- retrieval by `(source_id, source_version)`;
- Unicode scalar-value span indexing, inclusive/exclusive boundaries, and exact-version binding;
- structured schema validation and error responses;
- downstream contract compatibility;
- no LLM calls in validation/persistence tests;
- no audio, speech recognition, multi-resident processing, clinical reasoning, authentication, or external nursing-note ingestion;
- constitution compliance and absence of unrecorded design deviations.

## Append-only rule

If a gap is found, append a new `## Phase N: Convergence` section to `tasks.md`. Do not modify, renumber, reorder, or delete existing tasks. Do not modify `spec.md`, `plan.md`, `data-model.md`, `source-api.yaml`, or checklist markers as part of convergence.

If the gap changes requirements or design intent rather than implementation completeness, stop and direct the reviewer to `clarify.md`, then regenerate the affected derived artifacts before running convergence again.

New convergence tasks must:

- use the next sequential task IDs;
- include a `[US#]` label when tied to a user story;
- include `[P]` only when genuinely parallelizable;
- include an exact file path;
- state the unmet requirement or acceptance criterion;
- be ordered by severity: constitution violation, critical acceptance gap, high-integrity gap, then polish.

## Report format

```text
# Convergence Report

Status: CONVERGED | TASKS APPENDED | BLOCKED

## Checklist gate
- checked items: <count>
- unchecked items: <count>
- checklist markers changed: no

## Findings
- [C###] <severity> <requirement or invariant> — <current evidence> — <remediation task>

## Task changes
- existing tasks changed: no
- new convergence tasks appended: <count>
- phase: <phase name>

## Verification summary
- user stories: <pass/fail summary>
- acceptance scenarios: <pass/fail summary>
- FR-01: <pass/fail summary>
- evidence integrity: <pass/fail summary>
- constitution: <pass/fail/blocked summary>
```

## Exit conditions

### CONVERGED

Return `CONVERGED` only when all requirements, acceptance scenarios, plan decisions, tasks, and constitution constraints are satisfied. Leave `tasks.md` byte-for-byte unchanged when no gap exists. Recommend review or pull request preparation.

### TASKS APPENDED

Return `TASKS APPENDED` when one or more implementation gaps remain. Report the number and IDs of appended tasks, then recommend running `implement.md` followed by `converge.md` again.

### BLOCKED

Return `BLOCKED` when required artifacts cannot be read or a decision outside implementation scope is required. Do not invent a requirement or silently mark the feature complete.
