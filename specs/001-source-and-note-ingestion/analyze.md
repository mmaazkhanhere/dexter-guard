# Consistency Analysis: Source Transcript Ingestion and Evidence Reference Foundation

## Purpose

Perform a read-only consistency analysis across the feature specification, plan, data model, API contracts, tasks, constitution, and stated project requirements. Report conflicts, gaps, and ambiguities; do not silently repair them and do not modify application code.

This analysis must run after clarification, planning, checklist review, and task generation, and before implementation. If it finds issues, fix the artifact that owns the issue and run this analysis again.

## Invocation

```text
/speckit.analyze [focus area]
```

Optional focus areas include `scope`, `contracts`, `evidence integrity`, `version concurrency`, `tasks`, and `constitution`.

## Inputs

Read:

- `.specify/memory/constitution.md`
- `docs/architecture.md`
- `specs/001-source-and-note-ingestion/spec.md`
- `specs/001-source-and-note-ingestion/plan.md`
- `specs/001-source-and-note-ingestion/tasks.md`
- `specs/001-source-and-note-ingestion/data-model.md`
- `specs/001-source-and-note-ingestion/contracts/source-api.yaml`

Read `checklist.md` only to report whether requirements-quality review is complete; do not change its markers.

## Analysis rules

### Source-of-truth ownership

- Requirement intent belongs in `spec.md`.
- Technical choices and constraints belong in `plan.md`.
- Entity invariants belong in `data-model.md`.
- Transport schemas belong in `contracts/source-api.yaml`.
- Implementation work belongs in `tasks.md`.
- Reviewer-owned quality judgments belong in `checklist.md`.
- Clarification decisions must be folded back into `spec.md` and then propagated to derived artifacts.

### Required cross-checks

1. Every user story has independently testable acceptance scenarios.
2. Every FR requirement maps to acceptance coverage and at least one task.
3. Every acceptance-critical invariant has a test task.
4. Source ID/version identity is consistent across all artifacts.
5. Version writes specify atomicity, uniqueness, stale-write behavior, and no partial persistence.
6. Unicode span semantics are identical in spec, data model, API, and tests.
7. Structured single-resident validation does not imply semantic disambiguation.
8. API request/response schemas agree with the data model.
9. Task dependencies reflect the user-story order and no task references an unknown artifact.
10. No artifact introduces excluded functionality or external nursing-note ingestion.
11. Plan decisions do not contradict user-facing requirements.
12. Checklist state is reported but not changed.

## Report format

```text
# Analysis Report

Status: CLEAN | ISSUES FOUND | BLOCKED

## Critical conflicts
- [A###] <artifact and section> — <conflict> — <owning artifact to fix>

## Gaps
- [A###] <missing requirement, scenario, test, or task> — <owning artifact to fix>

## Ambiguities
- [A###] <question> — <impact> — <clarify question ID>

## Traceability summary
- FR-01: <acceptance scenarios> -> <tasks/tests>
- Evidence integrity: <invariants> -> <acceptance scenarios> -> <tasks/tests>

## Checklist gate
- checklist path: specs/001-source-and-note-ingestion/checklist.md
- checked items: <count>
- unchecked items: <count>

## Recommended remediation order
1. <source-of-truth fix>
2. <derived-artifact regeneration>
```

## Exit conditions

- `CLEAN`: no unresolved critical conflicts, gaps, or ambiguities remain; report checklist state separately.
- `ISSUES FOUND`: report findings and stop before implementation; do not modify source artifacts automatically.
- `BLOCKED`: required input such as the constitution or project requirements cannot be read; report the missing input and stop.

An `ISSUES FOUND` or `BLOCKED` result requires fixing the owning artifact and re-running analysis before `implement.md`.
