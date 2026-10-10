# Implementation Execution Record — Spec 003

## Current state

Implementation has **not** been started by this specification-artifact task. This record is the execution protocol for `tasks.md`; it is not evidence that code, tests, or an API already exist.

## Mandatory preflight

1. Read the AI Nursing Documentation Reliability Engine Constitution v1.0.0 and these artifacts: `spec.md`, `data-model.md`, `clarify.md`, `plan.md`, `tasks.md`, and `analyze.md`.
2. Read `checklist.md` without modifying it.
3. If any reviewer-owned checkbox is unchecked, ask the reviewer/user whether to proceed. Do not treat unreviewed requirements quality as approval and do not change checkboxes.
4. Confirm the Python/FastAPI/Pydantic/SQLite stack and update only implementation details consistent with the constitution; create an ADR for a material cross-component trade-off and do not broaden feature scope.

## Execution order

Execute T001 through T019 in their listed dependency order. Write the failing deterministic tests/fixtures in T004–T007 before beginning their corresponding implementation tasks T008–T012. Each task must preserve the following non-negotiable conditions:

- Claim output reflects only the exact candidate-note revision.
- Structured provider output is untrusted until schema and span validation pass.
- A validation failure returns/persists no partial claims.
- No code assigns evidence support, contradiction, truth, or clinical diagnosis.
- New note revisions are extracted independently.
- Synthetic-only data, explicit resident-identity state, append-only run provenance, redacted telemetry, and typed timeout/provider failures are maintained.
- Every successful/empty result carries immutable evidence-source metadata and atomically emits the required Spec 004 handoff event; this is not an evidence verdict.

## Completion evidence

Before marking implementation complete, retain the commands/results for formatting, static analysis, all Spec 003 automated tests, CLM-001 through CLM-016, failure and persisted-result tests, extraction-metric results, and the scope/redaction review. Then run the convergence audit. If it appends work, return to the relevant task phase rather than declaring completion.
