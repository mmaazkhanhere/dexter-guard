# Technical Plan: Nursing Note Generation

## Chosen stack

This feature will use a TypeScript service built with Fastify, TypeBox (or an equivalent JSON Schema-backed validator), PostgreSQL, and an existing project-approved LLM provider adapter. The contract is OpenAPI 3.1 JSON over HTTPS. Database migrations are managed with the repository's existing migration tool; if none exists, use Prisma migrations. Automated tests use Vitest, Fastify injection tests, and deterministic fixture-based provider stubs.

The design intentionally keeps LLM output untrusted until it passes runtime schema validation. No model output is directly persisted as a successful note.

## Architecture

```text
Source transcript (Spec 001) ─┐
                              ├─ POST /notes/generate ─> generation adapter ─> validator ─> note + facts
External candidate note ──────┴─ POST /notes/import ───────────────────────────────────────> note (+ supplied facts)
                                                                                              │
                                                                                              └─ DRAFT hand-off to downstream verification
```

### Components

1. **Notes API** validates request identity, source references, and request shape; it returns a draft representation or a controlled error.
2. **Source resolver** reads an existing source reference from Spec 001. It does not create or alter transcripts.
3. **Generation service** builds a constrained German documentation request and calls the provider through an adapter.
4. **Output validator** validates the provider result against a strict schema and runs deterministic source-fidelity guard checks before persistence.
5. **Notes repository** persists immutable note revisions, fact records, origin, source anchors, and auditable generation metadata in one transaction.
6. **Import service** stores the candidate note and supplied provenance without constructing or invoking the generation service.
7. **Downstream hand-off** publishes/returns only draft identifiers and provenance; it owns neither verification nor approval.

## API contracts

### `POST /api/v1/notes/generate`

**Request**

```json
{
  "sourceId": "src_...",
  "requestedBy": "user_..."
}
```

**Successful response — `201 Created`**

```json
{
  "noteId": "note_...",
  "revision": 1,
  "status": "DRAFT",
  "origin": "GENERATED",
  "content": "... German nursing note ...",
  "sourceId": "src_...",
  "facts": [
    {
      "factId": "fact_...",
      "type": "MEASUREMENT",
      "statement": "Körpertemperatur 38,2 °C gemessen.",
      "sourceAnchor": { "start": 14, "end": 39 },
      "polarity": "AFFIRMED",
      "certainty": "CERTAIN",
      "attribution": "CAREGIVER_OBSERVED",
      "value": "38,2",
      "unit": "°C"
    }
  ],
  "provenance": { "origin": "GENERATED", "generationRunId": "gen_..." }
}
```

**Errors**

- `404`: the requested source does not exist or is inaccessible.
- `422`: provider output is malformed, fails schema validation, or violates deterministic source-fidelity checks. The response includes a safe error code and correlation ID, never invented note content.
- `502`/`503`: provider unavailable or timed out. No success draft is created.

### `POST /api/v1/notes/import`

**Request**

```json
{
  "content": "... externally supplied German nursing note ...",
  "externalOrigin": { "system": "...", "reference": "..." },
  "requestedBy": "user_...",
  "facts": []
}
```

`facts` is optional and, when supplied, represents external data rather than generated extraction.

**Successful response — `201 Created`** returns the same draft envelope with `origin: "IMPORTED"`, `status: "DRAFT"`, and supplied provenance. This route has no dependency on the generation adapter.

## Persistence model

`note_drafts`: `id`, `status`, `origin`, `content`, `revision`, `previous_revision_id`, `source_id` nullable for import, `external_origin` JSON nullable, `created_at`, `created_by`, `generation_run_id` nullable.

`nursing_facts`: `id`, `note_draft_id`, `type`, `statement`, `source_anchor` JSON, `polarity`, `certainty`, `attribution`, `numeric_value`, `unit`, `provenance` JSON.

Use a uniqueness constraint on `(logical_note_id, revision)` and foreign keys from facts to the exact draft revision. Store model/provider IDs and prompt-template version as audit metadata, never hidden chain-of-thought.

## Generation and validation flow

1. Resolve the source transcript by ID and establish its immutable content/version reference.
2. Request a strict JSON object from the LLM: `content` plus facts with source offsets and fidelity fields.
3. Reject non-JSON or schema-invalid output.
4. Verify every fact source anchor resolves to the transcript, every measurement string/value/unit matches its anchored text, and all explicitly negated/uncertain/attributed source spans are reflected in corresponding generated output/facts.
5. Run lexical/pattern safety checks for introduced diagnostic assertions against a project-maintained diagnosis vocabulary. This is a generation guardrail, not downstream evidence verification.
6. Persist the draft and facts atomically with `status = DRAFT`.

## Test strategy

- API contract tests for validation, response shape, `DRAFT` status, and origin metadata.
- Deterministic fixture tests for GEN-001 through GEN-010.
- Mutation-style regression fixtures that invert negation, remove uncertainty/attribution, alter numbers/units, and introduce a diagnosis; each must fail generation validation.
- Import spy test proving the generation adapter is not called.
- Repository tests for revision lineage and atomic rollback on malformed output.
- Integration test with a provider stub; live-provider tests are non-blocking and must not be the acceptance oracle.

## Constitution alignment gate

Before implementation, map each task to the repository's `.specify.memory/constitution.md`, including its safety, data-handling, testing, and observability principles. If a project rule conflicts with this plan's illustrative stack choice, the constitutional/project rule wins and the plan must be amended before code is written.
