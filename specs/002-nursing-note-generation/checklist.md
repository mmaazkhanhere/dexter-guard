# Requirements Quality Checklist: Nursing Note Generation

**Reviewer-owned artifact.** Mark an item only after reviewing requirements quality; checked items do not mean implementation is complete.

## Constitution and scope

- [ ] All specification and plan references use `.specify/memory/constitution.md` and comply with its applicable principles.
- [ ] The feature is limited to drafting, structuring, import, provenance, and revision tracking; it does not verify or approve notes.
- [ ] FR-01 ownership remains with Spec 001 and Specs 004/006 retain comprehensive semantic/evidence judgment.

## Source and provenance

- [ ] Both generation and verification-ready import require a resolvable `sourceId` and exact `sourceVersion`.
- [ ] Imported external origin is explicitly distinct from the transcript evidence source.
- [ ] The data model prevents successful generated or imported revisions with null source ID/version.
- [ ] Revision lineage and fact provenance are sufficient for downstream review.

## Fidelity and failure behavior

- [ ] Limited deterministic guardrails are clearly bounded and are not presented as semantic/evidence verification.
- [ ] Fixed fixtures explicitly cover negation, uncertainty, attribution, numeric value, unit, malformed output, and prohibited diagnostic output.
- [ ] Failure behavior guarantees no partial draft/fact persistence.

## Acceptance and delivery

- [ ] The measurable schema, source-integrity, import-isolation, fixture, and draft-state thresholds are unambiguous.
- [ ] `data-model.md` and `contracts/notes-api.yaml` are present and consistent with `spec.md`.
- [ ] Tasks are grouped by independently testable generation, fact-extraction, and import stories and name planned implementation/test paths.
