# Technical Plan: Nursing Note Generation

## Constitution alignment

This design is governed by `.specify/memory/constitution.md`. It introduces no independent approval or verification capability, keeps a source-of-truth reference on every verification-ready note, treats generated material as an editable draft, and uses tests as the acceptance evidence. The implementation must use the repository's constitution-approved runtime, validation, persistence, testing, and provider-adapter conventions; this feature does not introduce a competing technology stack.

## Architecture

```text
immutable SourceDocument + sourceVersion
              │
     ┌────────┴─────────┐
     │                  │
generate                 import external candidate + externalOrigin
     │                  │
generation adapter       no generation-adapter call
     │                  │
strict schema + limited generation-time guardrails
     │                  │
     └──────> DRAFT note revision + source-linked facts ──────> downstream Specs 004/006
```

### Components

1. **Source resolver** resolves the immutable `SourceDocument` identified by `sourceId` and `sourceVersion`.
2. **Generation service** requests constrained German prose and facts only for `generate`.
3. **Schema/guardrail service** validates output structure, source anchors, explicitly represented fidelity fields, and exact measurement values/units. It does not certify semantic equivalence or evidence.
4. **Note repository** persists revision lineage, evidence-source fields, origin, content, and facts atomically.
5. **Import service** persists a supplied candidate and its `externalOrigin` against the same required evidence source, without depending on the generation service.
6. **Downstream hand-off** exposes only `DRAFT` records; verification and approval remain downstream.

## API design

`contracts/notes-api.yaml` is the normative API contract.

- `POST /api/v1/notes/generate` requires `sourceId`, `sourceVersion`, and requester identity.
- `POST /api/v1/notes/import` requires `content`, `sourceId`, `sourceVersion`, `externalOrigin`, and requester identity. It returns `201` only when the exact source version resolves.
- `422` represents malformed/schema-invalid provider output; the transaction rolls back.
- `404` means the source document/version is unavailable; `409` means the requested version cannot be used as the exact source version. Neither persists a note.

## Guardrail boundaries

The service validates contract shape and deterministic properties of fixed fixtures. It can prove that referenced spans exist, identifiers resolve, values/units match anchored source text, and explicitly represented fields have expected values. It cannot generally prove that free German prose is semantically equivalent to a source or that no clinical inference is implied. Therefore:

- validation success means **generation contract accepted**, never evidence-verified;
- GEN-010 is a fixed prohibited-output regression guardrail, not diagnosis detection in the general case;
- comprehensive semantic and evidentiary judgments are deferred to Specs 004 and 006.

## Persistence design

`data-model.md` is the normative persistence/domain contract. The critical invariant is that `note_revision.source_id` and `note_revision.source_version` are both non-null for generated and imported notes. `external_origin` is non-null only for imported notes and is not a foreign key or substitute for evidence source.

Persist a successful creation as one transaction: note revision, facts, provenance, and audit metadata. On any schema, guardrail, or source-resolution failure, commit none of them.

## Test design

- Contract tests compile/validate `contracts/notes-api.yaml` and assert request/response behavior.
- Fixture tests implement GEN-001 through GEN-010 with the exact expected outcomes in `spec.md`.
- Persistence tests assert source-version integrity, atomic rollback, origin separation, and immutable revision lineage.
- Import tests spy on the generation adapter and require zero invocations.
- No test may describe a generated note as evidence-verified merely because it passed Spec 002 validation.
