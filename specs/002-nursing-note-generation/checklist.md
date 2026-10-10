# Requirements Quality Checklist: Nursing Note Generation

**Reviewer-owned artifact.** Mark an item only after reviewing requirements quality; checked items do not mean implementation is complete.

## Constitution and scope

- [x] All specification and plan references use `.specify/memory/constitution.md` and comply with its applicable principles.
- [x] The feature is limited to drafting, structuring, import, provenance, and revision tracking; it does not verify or approve notes.
- [x] FR-01 ownership remains with Spec 001 and Specs 004/006 retain comprehensive semantic/evidence judgment.
- [x] The mandated Python/FastAPI/Pydantic/SQLite stack is explicit and no competing stack is introduced.

## Source and provenance

- [x] Both generation and verification-ready import require a resolvable `sourceId` and exact `sourceVersion`.
- [x] Imported external origin is explicitly distinct from the transcript evidence source.
- [x] The data model prevents successful generated or imported revisions with null source ID/version.
- [x] Facts require resident identity or explicit `UNKNOWN`, atomicity, temporal metadata, source-offset semantics, and validation-run provenance.
- [x] Revision lineage and fact provenance are sufficient for downstream review.

## Fidelity and failure behavior

- [x] Limited deterministic guardrails are clearly bounded and are not presented as semantic/evidence verification.
- [x] Fixed fixtures explicitly cover negation, uncertainty, attribution, numeric value, unit, malformed output, and prohibited diagnostic output.
- [x] Failure behavior guarantees no partial draft/fact persistence.
- [x] Synthetic-only data, append-only provenance, bounded retries/timeouts, idempotent runs, and content-minimized telemetry are specified.

## Acceptance and delivery

- [x] The measurable schema, source-integrity, import-isolation, fixture, and draft-state thresholds are unambiguous.
- [x] `data-model.md` and `contracts/notes-api.yaml` are present and consistent with `spec.md`.
- [x] Tasks are grouped by independently testable generation, fact-extraction, and import stories and name planned implementation/test paths.
