# Design Plan — Spec 003

## Architecture choice

Use a small, hexagonal Python claim-extraction module. It exposes one application service, `extract_claims(note_revision_id)`, and keeps the optional FastAPI endpoint as a thin adapter. Pydantic models are the domain/API contract; the domain service is independent of FastAPI, the extraction provider, persistence layer, and Spec 004.

```text
Stored Note Revision
        |
        v
Revision guard --> Extraction provider --> Schema/semantic validator --> Claim repository
                         |                         |
                         |                         +--> explicit FAILED / EMPTY / SUCCEEDED result
                         v
              structured candidate claims

Spec 004 / 005 / 007 consume only validated Claim records
```

## Proposed technology stack

Use the constitution-mandated Python/FastAPI/Pydantic/SQLite stack. Existing repository conventions may refine implementation details only when they do not replace these required boundaries.

| Concern | Choice | Rationale |
|---|---|---|
| Runtime and domain code | Python 3.12+ | Constitution-required backend platform; type hints and pure domain logic. |
| HTTP adapter (optional) | FastAPI | Constitution-required HTTP framework; handler delegates to service. |
| Contract validation | Pydantic v2 | Constitution-required cross-component/API payload validation and schema generation. |
| Persistence | SQLite for the local PoC, isolated behind a repository interface | Constitution-required local store; PostgreSQL may later replace only the adapter. |
| Extraction provider | Provider port returning schema-constrained JSON; deterministic rule-based pre/post validators | Provider can be swapped without changing Claim contract. |
| Tests | pytest, Hypothesis where boundary/property testing is useful, and synthetic fixtures | Unit, schema, service, API, acceptance, and evaluation coverage. |
| Observability | Existing structured logger/telemetry with protected-field redaction | Avoids exposing nursing-note content in logs. |

No transcript or evidence-system connector is introduced.

## Constitution Check

| Principle | Plan application | Verification evidence |
|---|---|---|
| I. Evidence fidelity | Emit atomic candidate-note assertions with exact revision provenance and carry the associated immutable source reference; do not call them evidence-supported. Spec 004 performs source-span alignment. | CLM-001–CLM-016, span/value tests, scope review. |
| II. Human authority/fail-safe review | Extraction never approves, repairs, or diagnoses. Invalid/absent extraction is explicit and blocks downstream verification readiness. | Failure-state and revision-isolation tests. |
| III. Spec-first delivery | `spec.md`, clarification record, plan, tasks, contract tests, and acceptance evidence precede implementation. | Checklist gate and task sequence. |
| IV. Contract-first modularity | Pydantic contracts, FastAPI OpenAPI, ports/adapters, immutable revision access, deterministic validators, versioned provider adapter. | Contract/API tests, schema version checks, adapter tests. |
| V. Evaluation release gate | Contribute labeled extraction cases to the shared Spec 008 benchmark and measure extraction precision/recall, span validity, semantic attributes, and failures. | Spec 003 evaluation report; system-wide thresholds remain Spec 008's gate. |
| VI. Privacy/provenance | Synthetic-only data; append-only run/revision/version metadata; content-minimized telemetry; SQLite repository. | Fixture audit, provenance tests, redaction tests. |
| VII. Observable failures | Typed failure outcomes, timeouts, bounded retries, idempotent run ids, metrics and warning counts. | Timeout/malformed-output/retry tests and telemetry inspection. |

## Components

| Component | Responsibility | Must not do |
|---|---|---|
| `NoteRevisionReader` port | Load immutable synthetic stored body, body hash, single resident test ID, source reference, declared language, and revision metadata. | Accept unverified replacement text or infer/disambiguate identity. |
| `ClaimExtractionService` | Orchestrate extraction, validation, result state, and persistence. | Verify claims against evidence. |
| `ClaimExtractionProvider` port | Produce candidate structured claims from German note text. | Persist output or assign truth status. |
| `ClaimValidator` | Validate schema, enums, required fields, spans, raw values, and cross-field invariants. | Repair invented data. |
| `SpanValidator` | Resolve code-point/UTF-16 coordinates and require exact substring equality. | Approximate locations. |
| `ClaimRepository` port | Persist versioned results and append-only extraction-run history transactionally by note revision. | Merge claim identities across revisions or assign verdicts. |
| HTTP adapter | Map a request to the service and return result/error. | Contain extraction policy. |

## Processing flow

1. Resolve the requested immutable synthetic note revision, evidence-source reference, body hash, and single resident test ID; reject missing, stale, changed-body, unsupported-language, non-synthetic, or missing-association requests explicitly.
2. Submit only the stored note text and non-evidentiary extraction instructions to the provider port.
3. Parse provider output as untrusted data.
4. Validate result schema, claim uniqueness, required claim text, enum values, source spans, cue/value spans, numeric raw-text fidelity, and revision identity.
5. Reject the whole result on invalid JSON, invalid invariants, or any mismatched location. Do not return partial claims.
6. If candidate output is empty, run a bounded independent factual-assertion safeguard. Persist/return `EMPTY` only when it also finds none; otherwise return typed `EMPTY_RESULT_UNCERTAIN` failure.
7. Transactionally persist the validated result, immutable evidence-source reference, and append-only extraction-run provenance with extractor/provider/model/prompt/schema versions. Make it the current extraction only for the exact revision/version policy.
8. Return the typed persisted result to callers. Spec 004 consumes it before a later workflow may treat the revision as verification-ready; this service does not call Spec 004 or assign an evidence verdict.

## Persistence model

Minimum logical records:

| Record | Key fields |
|---|---|
| `note_revision` | `id`, single resident test ID, immutable synthetic UTF-8 body, body hash, revision number, language |
| `claim_extraction_result` | `id`, `extraction_run_id`, `note_revision_id`, body hash, immutable evidence-source reference, extractor/provider/model/prompt/schema versions, discriminated status/error metadata, timestamps |
| `claim` | `id`, result id, ordinal, category, semantic fields, spans, raw claim text |

Use a SQLite transaction so a `FAILED` result does not leave claim rows and a successful result cannot point to a different body hash. Retain an append-only extraction-run record even for failures. Retain raw strings used for fidelity; normalized decimal values are supplementary.

## API design (optional adapter)

`POST /api/v1/claims/extract`

Request: `{ "noteRevisionId": "..." }`.

Success: `200` and `ExtractionResult` with `SUCCEEDED` or `EMPTY`.

Client/input error: `400` or `404` with a non-sensitive error code. Provider/validation failure: an explicit failure response (for example `422` for invalid provider output, `503` for retryable provider failure) containing no partial claims. Exact status mapping should follow repository conventions.

The service interface—not this route—is the acceptance-test target.

## Validation invariants

- `statementSpan.text === claimText` and resolves exactly against the stored revision in both coordinate systems.
- Every nested span is inside, or explicitly documented as overlapping, its statement span and resolves exactly.
- Every claim id is unique within one result; every claim refers to that result's revision.
- Every claim contains the single `residentTestId` from authoritative revision metadata; absence is a typed failure.
- `NEGATED` needs a direct negation cue; cues may not be silently synthesized.
- Non-`UNSPECIFIED` attribution needs direct textual attribution evidence.
- Each `NumericValue.raw`, value span, and unit span match the note exactly; normalized decimals are decimal strings, not binary floats.
- `FAILED` contains no claims and requires a typed error; `EMPTY` contains no claims and forbids an error.
- Every `SUCCEEDED`/`EMPTY` result has an immutable source reference and is retrievable by typed service/persisted record for Spec 004.
- Contract contains no evidence verdict, source transcript, diagnostic result, or support/contradiction field.
- Pydantic rejects invalid external/provider data before it enters the domain; FastAPI OpenAPI schema is versioned and contract-tested if exposed.

## Test strategy

Write tests before each implementation slice. Test through the application service with a fake provider and fixed synthetic stored-note fixtures. Add unit/property tests for validator and Unicode span conversion, contract tests for provider parsing, persisted-result/provenance tests, and acceptance tests for CLM-001 through CLM-016. Contribute labeled cases to the shared Spec 008 benchmark; this feature reports atomic-claim precision/recall, span validity, semantic-attribute accuracy, and failure-handling results. Use at least one Umlaut/emoji fixture to prove coordinate-system validation is not ASCII-only. HTTP tests are required only if the adapter is exposed.

## Operational and security constraints

- Enforce synthetic-only fixtures and requests; reject or quarantine data that is not approved synthetic PoC data according to repository policy.
- Redact note text, claim text, and prompt bodies from ordinary logs and errors; store secrets only in secure configuration.
- Version the provider prompt/schema/model/settings and record versions without recording sensitive content.
- Set explicit provider timeouts, bounded retries, and idempotent run identifiers; map failures without automatic fallback that could change claim semantics or duplicate actions.
- Add an ADR before implementation if the final design changes a cross-component contract, chooses a non-default provider boundary, or introduces a material trade-off.
