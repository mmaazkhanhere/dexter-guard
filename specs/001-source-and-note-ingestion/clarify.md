# Clarification Workflow: Source Transcript Ingestion and Evidence Reference Foundation

## Purpose

Resolve requirements-level ambiguity before planning or implementation. This workflow asks targeted questions, records answers, and folds accepted decisions back into `spec.md` before `plan.md` or `tasks.md` are generated or trusted.

This is a requirements clarification artifact, not an implementation task list. It must not introduce application code, resident disambiguation, speech recognition, authentication, clinical reasoning, or external nursing-note ingestion.

## Invocation

Run this clarification workflow from the repository root, optionally with a focus area:

```text
/speckit.clarify [focus area]
```

Examples:

```text
/speckit.clarify source versioning and concurrency
/speckit.clarify Unicode evidence spans
/speckit.clarify API input validation
```

If no focus area is supplied, review all unresolved requirements in priority order: scope, source identity/versioning, evidence integrity, input validation, then API representation.

## Inputs

Read these artifacts before asking questions:

1. `.specify/memory/constitution.md`
2. `docs/architecture.md`
3. `specs/001-source-and-note-ingestion/spec.md`
4. `specs/001-source-and-note-ingestion/plan.md`, when it exists
5. `specs/001-source-and-note-ingestion/data-model.md`
6. `specs/001-source-and-note-ingestion/contracts/source-api.yaml`

Do not treat `tasks.md` or implementation code as a source of requirements intent.

## Clarification rules

- Ask only questions whose answers can materially change scope, acceptance behavior, data integrity, or user-visible contracts.
- Prefer a reasonable default and record it as an assumption when the choice does not materially affect behavior.
- Limit one clarification run to the three highest-impact unresolved questions.
- Do not ask the user to choose implementation details when the requirements already imply a safe default.
- Never infer residents from transcript meaning. Single-resident validation is limited to structured input containing exactly one scalar `resident_test_id`.
- Never introduce an LLM call to resolve an ambiguity in this feature.
- Preserve resolved answers in `spec.md`; do not leave important decisions only in chat history.

## Targeted questions for this feature

### Q1 — FR-01 wording and input boundary

Does project FR-01 mean that the API must accept a JSON request containing exactly one scalar `resident_test_id`, `language: de-DE`, and a non-blank `transcript_text`, with no semantic inspection of the transcript for resident identity?

Default if unanswered: yes. Record the exact FR-01 identifier and wording from `docs/functional_requirements.md` in the requirement traceability table.

### Q2 — Initial submission versus revision

Should every new submission create a new `source_id` at version `1`, while revisions require an existing `source_id` plus `expected_source_version` and atomically create the next version?

Default if unanswered: yes. A stale or concurrent revision returns `409 VERSION_CONFLICT`; no source version is overwritten.

### Q3 — Unicode span contract

Should `start` and `end` be zero-based Unicode scalar-value/code-point offsets, with inclusive `start`, exclusive `end`, no Unicode normalization, and line endings counted exactly as stored?

Default if unanswered: yes. UTF-8 byte offsets, UTF-16 code-unit offsets, and grapheme-cluster indexing are not part of the source contract.

## Resolution record

Record each answer using this format, then update `spec.md`, `plan.md`, and affected contracts/tasks as appropriate:

```text
Question: Q###
Answer: <user-confirmed decision>
Decision: <requirement or invariant added/changed>
Spec sections updated: <headings and paths>
Downstream artifacts requiring regeneration: <plan/tasks/API/data model>
Status: Resolved | Deferred with explicit owner/date
```

## Completion gate

Clarification is complete when:

- no material `[NEEDS CLARIFICATION]` markers remain in `spec.md`;
- each accepted answer is folded into the source-of-truth requirement;
- the data model and API contract reflect the resolved behavior;
- `plan.md` records any resulting design decision;
- `tasks.md` is regenerated or updated to match;
- unresolved items are explicitly listed with an owner or a documented safe default.

After this gate, run `checklist.md`, then `analyze.md`, before `implement.md`.
