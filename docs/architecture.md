# Dexter Guard Architecture

## 1. Purpose

Dexter Guard is an evidence-oriented system for working with German nursing transcripts about synthetic residents. Its architecture is organized around identifiable source data, explicit contracts, immutable revisions, and traceable references between source material and downstream artifacts.

The system must make it possible to answer:

- Which source document was used?
- Which immutable version was used?
- Which synthetic resident does it concern?
- Which character range supports an observation, fact, or finding?
- Which revision and decision produced the final result?

The architecture therefore treats provenance as a first-class concern rather than as metadata attached to arbitrary text.

## 2. Architectural principles

### Source-first processing

All downstream artifacts originate from a persisted `SourceDocument`. Components must not accept unreferenced transcript text as authoritative input.

### Immutable evidence

Accepted source versions are immutable. Corrections and revisions create new versions; existing versions remain retrievable.

### Explicit contracts

Domain boundaries communicate through documented contracts rather than shared, unstructured dictionaries or implicit text conventions.

### Traceability by construction

Artifacts that depend on source material carry stable source references. Evidence is represented using `SourceSpan`, which identifies an exact character range in an exact transcript version.

### Deterministic foundations

Validation, persistence, identifier generation, versioning, and span resolution must be testable without an LLM provider or network access.

### Narrow proof-of-concept scope

The first implementation prioritizes reliable source ingestion and contract foundations. Domain-specific verification behavior is layered on top and does not weaken source guarantees.

## 3. Scope and system boundary

### In scope

- Accepting one German text transcript concerning one synthetic resident.
- Validating request format and schema.
- Assigning a unique source identifier.
- Preserving immutable source versions.
- Persisting and retrieving source documents by ID and version.
- Validating and resolving source character spans.
- Providing stable contracts for downstream note, fact, claim, evidence, review, and evaluation components.
- Producing structured validation and lookup errors.

### Out of scope for the proof of concept

- Audio input and speech recognition.
- Multi-resident disambiguation or resident identification from ambiguous transcripts.
- Medical accuracy determination or autonomous clinical judgment.
- Production authentication and authorization.
- Silent source overwrites.
- An LLM requirement for validation or persistence tests.

Any future model-assisted or verification component must consume the source contracts defined here and must not replace the source repository as the authority for transcript content.

## 4. Logical architecture

```text
                         +----------------------+
                         | Demo/API client       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | API boundary         |
                         | request parsing      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Schema validation    |
                         | structured errors    |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Source service       |
                         | IDs + versions       |
                         | immutability rules   |
                         +----+------------+----+
                              |            |
                              v            v
                    +----------------+  +----------------+
                    | Source         |  | Span validator |
                    | repository     |  | and resolver   |
                    +-------+--------+  +--------+-------+
                            |                    |
                            +---------+----------+
                                      v
                         +----------------------+
                         | Downstream contracts |
                         | notes, facts, claims |
                         | findings, reviews,   |
                         | evaluation cases    |
                         +----------------------+
```

The API boundary is responsible for transport concerns. The source service owns source identity and version rules. The repository owns durable storage and retrieval. The span validator owns source/version existence checks and character-boundary validation. Downstream components consume contracts and references but do not mutate source data.

## 5. Component responsibilities

### API boundary

Responsibilities:

- Accept structured text-submission requests.
- Reject malformed requests before domain processing.
- Map domain errors to stable response shapes.
- Expose source creation, source-version creation, source retrieval, and span resolution.
- Return source identity and version information to callers.

The API boundary must not perform medical reasoning or silently coerce invalid input.

### Validation component

Responsibilities:

- Confirm that the transcript is text and non-blank.
- Confirm that exactly one synthetic resident test ID is supplied.
- Confirm that the supported language/locale is `de-DE`.
- Reject unsupported input types such as audio.
- Validate source-span structure and source-dependent boundaries.
- Return a stable error code, message, and field/path where applicable.

Schema validation is distinct from clinical or semantic validation. A syntactically valid transcript is accepted as source data even when its observations have not been medically verified.

### Source service

Responsibilities:

- Create a unique `source_id` for every initial source submission.
- Create version `1` for a new source.
- Create the next explicit version for a source revision.
- Prevent overwrites and duplicate `(source_id, source_version)` identities.
- Preserve the resident association across versions.
- Delegate persistence and retrieval to the repository.

### Source repository

Responsibilities:

- Persist `SourceDocument` records using `(source_id, source_version)` as the logical key.
- Retrieve an exact source version.
- Check source/version existence.
- Preserve historical versions.
- Return the original transcript text exactly as stored.

The proof of concept may use an in-memory implementation behind a repository interface. The interface must allow a durable implementation without changing the public source contracts.

### Span validator and resolver

Responsibilities:

- Resolve the exact referenced source version.
- Validate `0 <= start < end <= character_length(transcript_text)`.
- Reject negative, empty, reversed, and out-of-range spans.
- Reject missing sources and versions.
- Return a derived excerpt only alongside its authoritative `SourceSpan`.

The resolver must apply one documented character-offset convention consistently. The canonical convention is zero-based, inclusive `start`, and exclusive `end`.

### Downstream domain components

Downstream components may add domain-specific behavior while preserving source provenance:

| Contract | Architectural role |
| --- | --- |
| `NursingNote` | Represents a note or note revision linked to a source ID and version. |
| `SourceFact` | Represents a source-linked fact and its supporting span(s). |
| `Claim` | Represents a claim that may be associated with note revisions and source references. |
| `EvidenceFinding` | Represents a verification outcome justified by source spans. |
| `ReviewDecision` | Represents a review result tied to stable reviewed artifacts. |
| `EvaluationCase` | Represents a benchmark input using the same source contract. |

These components must not introduce alternate source identifiers or copy transcript text as an untraceable authority.

## 6. Core data contracts

### SourceDocument

```text
SourceDocument {
  source_id: string
  source_version: positive integer
  resident_test_id: string
  language: "de-DE"
  transcript_text: non-blank string
  created_at: timestamp
}
```

`SourceDocument` represents one immutable source version. The source identity is `(source_id, source_version)`.

### SourceSpan

```text
SourceSpan {
  source_id: string
  source_version: positive integer
  start: non-negative integer
  end: positive integer
}
```

`SourceSpan` is valid only when its source/version exists and its boundaries are valid for that exact transcript version.

### Structured errors

Errors use a stable shape:

```text
Error {
  code: string
  message: string
  field/path: optional string
}
```

Recommended source-related codes include `INVALID_REQUEST`, `INVALID_TRANSCRIPT`, `INVALID_RESIDENT_TEST_ID`, `UNSUPPORTED_INPUT_TYPE`, `SOURCE_NOT_FOUND`, `SOURCE_VERSION_NOT_FOUND`, `DUPLICATE_SOURCE_VERSION`, and `INVALID_SOURCE_SPAN`.

## 7. Primary data flows

### New transcript ingestion

1. A client submits one structured German transcript and one synthetic resident test ID.
2. The API boundary parses the request.
3. Schema validation rejects malformed or unsupported input.
4. The source service assigns a unique `source_id` and version `1`.
5. The repository persists the exact transcript and metadata.
6. The API returns the immutable source identity.

No LLM call or medical judgment is required in this flow.

### Source revision

1. A client identifies an existing `source_id`.
2. The API validates replacement transcript data and resident identity.
3. The source service determines the next version.
4. The repository creates a new record without modifying older records.
5. The API returns the new `(source_id, source_version)`.

Existing spans remain tied to their original version and are not silently redirected to the new text.

### Evidence span resolution

1. A client submits a `SourceSpan`.
2. The resolver retrieves the exact source version.
3. The resolver checks the character boundaries.
4. A valid request returns the derived excerpt with the original span reference.
5. An invalid request returns a structured error.

### Downstream consumption

1. A downstream component receives a source-linked contract.
2. It retains the source ID and version.
3. It uses `SourceSpan` for evidence locations.
4. Review and evaluation artifacts retain stable references to the source-linked artifact.
5. Source retrieval remains the authority for transcript content.

## 8. API boundary

The source API should provide these transport-independent operations:

| Operation | Purpose |
| --- | --- |
| Create source | Accept a new transcript and create version 1. |
| Create source version | Add an immutable revision to an existing source. |
| Get source version | Retrieve exact source data by ID and version. |
| Resolve source span | Validate and resolve a character range. |

The normative request and response schemas are defined in `specs/001-source-and-note-ingestion/contracts/source-api.yaml`.

## 9. Persistence and consistency

The repository must provide atomic creation of a source version. A failed validation must not leave a partial record. A duplicate version must fail rather than overwrite an existing record.

The persistence model must support:

- lookup by `source_id` and `source_version`;
- historical version retrieval;
- source/version existence checks;
- exact text round-tripping;
- deterministic test fixtures;
- replacement of in-memory storage with durable storage later.

Concurrency behavior should preserve the uniqueness of `(source_id, source_version)`. When two revisions race, only one may claim a given next version; the other must receive a conflict or retryable error rather than overwrite data.

## 10. Non-functional requirements mapping

### Reliability

Use explicit repository operations, immutable records, duplicate-key protection, and retrieval tests to ensure accepted source data remains available and unchanged.

### Traceability

Require source ID and version on evidence-bearing references. Resolve spans only against the exact referenced version.

### Reproducibility

Use deterministic validation, stable error codes, fixed test fixtures, and injectable ID/time providers where practical.

### Maintainability

Keep transport, validation, source service, persistence, and downstream contracts separated behind small interfaces.

### Testability

Test validation, persistence, versioning, and span resolution without an LLM provider, audio pipeline, external network, or medical reasoning service.

### Data integrity

Preserve source text exactly, reject invalid boundaries, and prevent silent mutation or deletion of source versions.

### Extensibility

Allow downstream note, fact, claim, evidence, review, and evaluation components to evolve independently while depending on stable source contracts.

## 11. Security and privacy boundary

The proof of concept uses synthetic resident data and does not introduce production authentication or authorization. This does not remove the need to avoid unnecessary data exposure in logs and error messages.

Future production hardening should address authentication, authorization, audit logging, encryption, retention, and operational secret management as a separate scope of work.

## 12. Testing architecture

The test suite should be layered:

### Contract tests

Verify required fields, types, enum values, error shapes, and source-span semantics.

### Service tests

Verify unique IDs, version sequencing, resident consistency, immutability, and duplicate prevention using a repository fake.

### Repository tests

Verify exact persistence round-trips, historical retrieval, missing-record behavior, and source/version uniqueness.

### API tests

Verify successful submission, structured validation errors, retrieval, revision, and span resolution through the demo/API boundary.

### Scope tests

Verify audio input, multi-resident input, and unsupported request shapes are rejected. Verify that these tests do not require an LLM.

## 13. Architectural decisions

| Decision | Rationale |
| --- | --- |
| Composite source identity | Prevents ambiguity when a logical source has multiple immutable versions. |
| New source ID for each initial submission | Ensures every accepted source document is independently identifiable. |
| Explicit revision operation | Prevents accidental overwrites and makes history visible. |
| Character spans instead of copied excerpts | Keeps evidence anchored to authoritative source data. |
| Repository interface | Supports deterministic tests and future durable persistence. |
| Structured errors | Makes API behavior predictable for demos and downstream consumers. |
| No LLM dependency in the foundation | Keeps ingestion, validation, and persistence deterministic and independently testable. |

## 14. Completion criteria

The architecture is implemented when:

- a valid German text transcript can be submitted;
- blank, malformed, unsupported, and structurally invalid submissions fail with structured errors;
- every accepted initial source has a unique ID and version 1;
- source text is preserved exactly;
- explicit revisions preserve all prior versions;
- sources are retrievable by ID and version;
- valid spans resolve against the correct version;
- invalid span boundaries are rejected;
- downstream contracts can retain source references;
- tests run without an LLM provider;
- excluded capabilities are not introduced into the proof-of-concept architecture.
