# Implementation Record: Nursing Note Generation

## Gate status

**Implemented on branch `feat/002-nursing-note-generation`.** The reviewer-owned `checklist.md` remains unchanged because it is a reviewer-owned requirements-quality artifact; its unchecked markers do not represent implementation status.

## Required implementation invariants

- Every generated or imported note has a resolvable `sourceId` and exact `sourceVersion`.
- Every fact has a resident identifier or explicit `UNKNOWN`, atomic source meaning, and valid source-offset semantics.
- Generated fact anchors are bounded to one source sentence, and explicit temporal qualifiers are preserved by deterministic guardrails; neither rule claims general semantic verification.
- Imported `externalOrigin` identifies candidate provenance only; it is not evidence.
- Every successful result starts in `DRAFT` and is neither verified nor approved.
- Guardrail success means only that the generation contract was accepted; it is not evidence verification.
- Import invokes the generation adapter zero times.
- Only synthetic German data is used; provider failures are explicit, provider timeout/retry behavior is bounded, run IDs are idempotent across retries, and telemetry is content-free.

## Implementation mapping

- Runtime contracts and response metadata: `src/nursing_notes/contracts.py`.
- Provider boundary and offline CI adapter: `src/nursing_notes/adapters.py`.
- Source-anchor and bounded fidelity guardrails: `src/nursing_notes/guardrails.py`.
- Generated/imported draft services and revision lineage: `src/nursing_notes/service.py`.
- Atomic SQLite note revision/fact persistence, with an explicit in-memory test double: `src/nursing_notes/repository.py`.
- FastAPI endpoints and error mapping: `src/source_ingestion/app.py`.
- Contract and acceptance coverage: `tests/nursing_notes/`.
- Boundary decision record: `docs/adr/002-nursing-note-generation-boundaries.md`.

## Verification record

- `uv run pytest`: **56 passed**, 0 failed, 0 skipped.
- `uv run python -m compileall -q src tests`: passed.
- `notes-api.yaml` parsed successfully with PyYAML.
- `git diff --check`: passed.
- GEN-007 verifies zero generation-adapter invocations on successful import.
- GEN-008 and provider-failure cases verify controlled errors with zero persisted notes/facts.
- All successful creation paths return `DRAFT`; no approval or verification transition is implemented.
- T022 observability tests verify bounded timeout/retry behavior, stable run IDs, rejection counters, and content-free metrics.
- Reviewer remediation tests cover SQLite round-trip/append-only history, API schema alignment, changed units, material source-span omission, draft-to-source mismatch, complete external provenance, and non-overlapping timeout behavior.
- Final checklist remediation tests cover temporal-qualifier retention, sentence-bounded fact anchors, mutually exclusive source/external anchors, and the Spec 001 `transcript_text` contract name.

## Bounded limitation

The live provider remains unconfigured by default, so timeout/retry behavior is exercised with deterministic synthetic adapters. This implementation does not claim live-model reliability, semantic equivalence, evidence verification, diagnosis detection in general, or benchmark completion.
