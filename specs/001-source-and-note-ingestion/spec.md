# Feature Specification: Source Transcript Ingestion and Evidence Reference Foundation

Feature Branch: `001-source-and-note-ingestion`

Created: 2026-10-09

Status: Draft

Input: Establish an immutable, versioned source of truth for German nursing transcripts and shared evidence-reference contracts.

## Goal

Establish a reliable, immutable, versioned source of truth for German nursing transcripts and define the foundational data contracts that enable evidence-based verification throughout the system.

A successful implementation guarantees that downstream components work with identifiable source data rather than arbitrary text without provenance.

## Scope

This specification owns the shared foundations for accepting, validating, identifying, versioning, persisting, retrieving, and referencing one German-language transcript concerning one synthetic resident.

It owns the complete `SourceDocument` contract and the reusable `SourceSpan` value object. It defines the source-related fields and invariants that downstream contracts depend on, but it does not implement those domain-specific contracts in full.

The proof of concept supports text transcripts only. It does not support audio input, speech recognition, multiple-resident disambiguation, production authentication, or LLM-backed processing.

## Non-goals

- Determining whether caregiver observations are medically accurate.
- Medical reasoning, verification prompts, or evidence interpretation.
- Extracting notes, facts, claims, findings, review decisions, or evaluation judgments.
- Integrating an LLM provider.
- Speech-to-text or other audio processing.
- Processing a transcript containing multiple residents.
- Production-grade authentication or authorization.

Input validation in this specification means validating the accepted format and schema. It does not mean validating the clinical truth of the submitted observations.

## User Scenarios & Testing

### User Story 1 - Submit an identifiable German transcript (Priority: P1)

As a client of the demo/API, I want to submit one structured German transcript for one synthetic resident so that the system creates an identifiable source of truth.

Why this priority: This is the minimum source-ingestion capability. Every downstream artifact depends on a persisted source identity and exact source text.

Independent Test: Submit a valid JSON request containing one `resident_test_id`, `language: de-DE`, and non-blank `transcript_text`; verify a successful response with a unique `source_id`, version `1`, and an exact text round trip.

Acceptance Scenarios:

1. Given a well-formed request with one scalar `resident_test_id` and non-blank German text, when the client submits it, then the API persists the transcript as version `1` and returns a unique `source_id`.
2. Given a missing, blank, non-string, or structurally malformed transcript, when the client submits it, then the API returns a structured validation error and persists nothing.
3. Given a request with an array or multiple resident identifiers, when the client submits it, then the API rejects the request as structurally invalid without attempting resident disambiguation.
4. Given accepted transcript text containing German diacritics, combining marks, punctuation, whitespace, or line breaks, when the client retrieves it, then the returned text is unchanged.

### User Story 2 - Preserve and retrieve source versions (Priority: P1)

As a source maintainer, I want revisions to create immutable, retrievable versions so that evidence never silently moves to different transcript text.

Why this priority: Version identity is required for reliable provenance and for every evidence-bearing downstream contract.

Independent Test: Create a source, create a revision with the expected current version, retrieve both versions, and verify that the first record is unchanged. Attempt a concurrent or stale revision and verify a conflict response.

Acceptance Scenarios:

1. Given an existing source at version `v`, when a revision is submitted with `expected_source_version: v`, then the system atomically creates version `v + 1` and leaves version `v` unchanged.
2. Given two revisions based on the same expected version, when both attempt creation, then exactly one succeeds and the other receives `409 VERSION_CONFLICT` or an equivalent stable conflict error.
3. Given a source ID and version, when a client retrieves them, then the exact immutable `SourceDocument` is returned; missing IDs or versions return structured not-found errors.

### User Story 3 - Reference exact evidence spans (Priority: P1)

As a downstream verifier, I want to reference an exact Unicode source range in an exact source version so that evidence findings remain reproducible.

Why this priority: Evidence references are the shared foundation for facts, findings, reviews, and benchmark cases.

Independent Test: Create a transcript containing non-ASCII and combining Unicode characters, submit valid and invalid spans, and verify that resolution uses the documented scalar-value indexing semantics.

Acceptance Scenarios:

1. Given a valid `(source_id, source_version)` and `0 <= start < end <= scalar_value_length(transcript_text)`, when the span is resolved, then the API returns the derived substring for that exact version.
2. Given a negative, empty, reversed, or out-of-range span, when it is resolved, then the API rejects it with `INVALID_SOURCE_SPAN`.
3. Given a span for a missing source or version, when it is resolved, then the API returns a structured not-found error.
4. Given a span calculated against one version but submitted with another version, when it is resolved, then the API validates it against the referenced version and does not silently redirect it.

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | The system shall accept one structured German text transcript with exactly one scalar `resident_test_id` and persist it as an immutable source version. |
| FR-02 | The system shall reject blank, non-text, malformed, unsupported, and structurally invalid submissions with structured validation errors. |
| FR-03 | The system shall assign a unique `source_id` to every initial accepted transcript. |
| FR-04 | The system shall preserve the original transcript text exactly. |
| FR-05 | The system shall create revisions atomically and preserve all prior versions. |
| FR-06 | The system shall detect stale or concurrent revisions and return a stable conflict response without overwriting data. |
| FR-07 | The system shall retrieve a source by `source_id` and `source_version`. |
| FR-08 | The system shall validate `SourceSpan` references against the exact Unicode source version. |
| FR-09 | The system shall expose the documented source contracts to downstream components. |

## Unicode source-span indexing

Offsets are zero-based indices over Unicode scalar values (Unicode code points), not UTF-8 bytes, UTF-16 code units, or user-perceived grapheme clusters. `start` is inclusive and `end` is exclusive.

The stored transcript is not Unicode-normalized before indexing or persistence. Each Unicode scalar value in the exact stored string contributes one index position. A base character and a combining mark therefore occupy separate positions; a grapheme cluster may be split by a technically valid span. Newline characters are indexed exactly as stored: a CRLF sequence contributes two scalar values, while LF contributes one. Implementations must not normalize line endings or apply NFC/NFD normalization before calculating offsets.

For a transcript `T`, a span is valid only when:

```text
0 <= start < end <= number_of_unicode_scalar_values(T)
```

The resolved excerpt is the substring from scalar-value index `start` through `end - 1`. The API, persistence layer, and tests must use this same convention.

## Capabilities

### 1. Transcript acceptance

The system accepts one German-language text transcript for one synthetic resident per submission.

The accepted input is a text value together with exactly one synthetic resident test ID. The transcript is treated as source material; ingestion must not normalize, summarize, translate, correct, or otherwise alter its content.

Audio input and submissions that require identifying or separating multiple residents are out of scope and must not be accepted as supported input.

### 2. Input validation

The API/demo boundary validates the input format and schema before persistence.

At minimum, validation must reject:

- a missing transcript;
- a blank transcript, including whitespace-only text;
- a non-text transcript value;
- a missing, blank, or malformed synthetic resident test ID;
- a missing, repeated, array-valued, or otherwise schema-invalid `resident_test_id` field;
- unsupported audio or other non-text input;
- malformed structured requests.

Validation failures use a structured error shape with a stable error code, a human-readable message, and the field or path that failed when applicable. Validation must be deterministic and must not call an LLM.

Validation does not inspect transcript meaning to infer, disambiguate, or verify residents, and does not assess whether observations are medically accurate.

### 3. Source identification

Every accepted transcript receives a globally unique `source_id` assigned by the ingestion boundary. The identifier is stable for the lifetime of that source version and is returned to the caller.

The source identity must not be derived solely from transcript text, because identical text submitted as separate source documents must remain separately identifiable.

### 4. Version management

Source data is immutable after acceptance. A new submission or correction creates a new source version; it must never silently overwrite an existing version.

Each version has a stable version identifier or monotonically unambiguous version number, an immutable transcript payload, and creation metadata. Older versions remain retrievable by their source ID and version.

The system must make the source/version pair explicit in every source reference. A reference that identifies only a source without a version is insufficient for evidence-bearing operations.

### 5. Evidence referencing

The system defines `SourceSpan` as the reusable value object for locating evidence in a specific transcript version.

A source span contains:

- `source_id`;
- `source_version`;
- `start` character offset, inclusive;
- `end` character offset, exclusive.

Offsets are zero-based character offsets into the stored transcript text. The span text is derived from the referenced immutable transcript version and is not an independently authoritative copy.

Valid spans satisfy `0 <= start < end <= unicode_scalar_value_length(transcript)`. The referenced source ID and version must exist, and the boundaries must be valid for that exact transcript version. Invalid, reversed, empty, out-of-range, or cross-version spans are rejected.

The implementation must document its character-offset convention and apply it consistently across API responses, persistence, tests, and downstream consumers.

### 6. Data persistence

Accepted source documents and their versions are persisted reliably and can be retrieved by source ID and version.

Persistence must preserve the original transcript text exactly, including meaningful whitespace, punctuation, casing, line breaks, and non-ASCII German characters. Retrieval must return the same source payload that was accepted.

Persistence behavior must be covered by tests that do not call an LLM.

## Foundational contracts

### `SourceDocument`

`SourceDocument` is the primary contract owned by this specification. It represents one immutable version of one transcript source.

Required fields:

| Field | Type | Requirements |
| --- | --- | --- |
| `source_id` | string | Globally unique, stable source identifier. |
| `source_version` | positive integer or equivalent explicit version value | Identifies this immutable version; unique within `source_id`. |
| `resident_test_id` | string | Exactly one synthetic resident test ID. |
| `language` | string | Must be `de-DE` for this proof of concept. |
| `transcript_text` | string | Non-blank original German transcript, stored unchanged. |
| `created_at` | timestamp | Creation time for this source version. |

Implementations may add persistence metadata, but additions must not change the meaning of the required fields or make the source text mutable.

The source identity is the pair `(source_id, source_version)`. Every initial submission creates a new unique `source_id` at `source_version = 1`. A later revision is allowed only through an explicit versioned operation for that `source_id`, which creates the next version and preserves every prior version. Version creation atomically checks the expected current version and inserts the next version under a uniqueness constraint on `(source_id, source_version)`. A stale or concurrent revision fails with `409 VERSION_CONFLICT` (or the equivalent stable conflict code) and persists nothing. A normal submission must never overwrite an existing source or version.

### `SourceSpan`

`SourceSpan` is the reusable evidence-reference value object owned by this specification. It must identify the exact source version and a valid character range within that version.

Required fields:

| Field | Type | Requirements |
| --- | --- | --- |
| `source_id` | string | Must identify an existing source. |
| `source_version` | version value | Must identify an existing version of `source_id`. |
| `start` | non-negative integer | Inclusive zero-based Unicode scalar-value/code-point offset. |
| `end` | positive integer | Exclusive zero-based Unicode scalar-value/code-point offset; must be greater than `start`. |

Consumers may resolve a span to its source text, but must not treat a copied excerpt as authoritative without retaining the source reference.

## Contract relationships

Spec 001 defines the shared source identity and span semantics used by the rest of the system:

| Contract | Relationship to Spec 001 |
| --- | --- |
| `SourceDocument` | Primary ownership: complete source schema, identifiers, and version. |
| `SourceSpan` | Primary ownership: reusable evidence-reference value object. |
| `NursingNote` | Depends on `source_id` and source version; note-specific fields belong to its owning specification. |
| `SourceFact` | Uses source references and spans; fact extraction and semantics belong elsewhere. |
| `Claim` | Uses source-linked note revisions indirectly; claim behavior belongs elsewhere. |
| `EvidenceFinding` | Uses source spans to justify verification outcomes; finding behavior belongs elsewhere. |
| `ReviewDecision` | Uses stable references to reviewed artifacts; review behavior belongs elsewhere. |
| `EvaluationCase` | Uses the same source contract for benchmark inputs; evaluation behavior belongs elsewhere. |

Spec 001 must not implement the complete domain behavior of the dependent contracts.

## API behavior

The demo/API exposes at least these operations:

### Submit a transcript

Accept a structured request containing exactly one transcript and one synthetic resident test ID. On success, persist an immutable source version and return its source ID, version, resident test ID, language, and creation timestamp.

On failure, return a structured validation error without persisting a partial source.

### Retrieve a source version

Given `source_id` and `source_version`, return the exact persisted `SourceDocument` or a structured not-found error. Retrieval must be deterministic and must not call an LLM.

### Create a source version

Given an existing `source_id` and replacement transcript content for the same synthetic resident, create the next immutable `source_version` without changing any prior version. The operation must reject a resident change, preserve the original source text, and return the new source/version identity.

### Validate or resolve a source span

Given a `SourceSpan`, verify that its source/version exists and that its boundaries are valid against that exact transcript. Return the resolved excerpt only as a derived view; the source reference remains authoritative.

The exact transport (HTTP, CLI, or in-process demo API) may follow the repository's existing conventions, but the documented contract and behaviors must remain transport-independent.

### Atomic versioning requirements

The versioned write operation accepts an `expected_source_version` and performs the expected-version check plus insertion of the next immutable version in one transaction. Persistence must enforce uniqueness of `(source_id, source_version)`. If the expected version is stale, or a concurrent revision wins the uniqueness race, the operation returns `409 VERSION_CONFLICT` (or an equivalent stable conflict code), persists no partial record, and leaves all prior versions unchanged. The resident test ID and language are inherited from the existing source and are not mutable through revision input.

## Error contract

All rejected requests use a structured error response with:

- a stable machine-readable `code`;
- a human-readable `message`;
- a `field` or `path` when the failure is tied to an input location.

At minimum, the implementation should distinguish blank or invalid transcript input, invalid resident ID, unsupported input type, malformed request, source not found, version not found, invalid source span, and stale or concurrent version creation (`VERSION_CONFLICT`).

Errors must not expose a partially persisted document and must not be used to silently coerce invalid input into a valid source.

## Acceptance criteria

| ID | Acceptance criterion |
| --- | --- |
| AC-001 | A valid German text transcript can be submitted through the demo/API. |
| AC-002 | A blank transcript is rejected with a structured validation error. |
| AC-003 | Every accepted transcript receives a unique source ID. |
| AC-004 | Each transcript is associated with exactly one synthetic resident test ID. |
| AC-005 | The original text remains unchanged after ingestion. |
| AC-006 | Source versions are distinguishable and older versions remain retrievable. |
| AC-007 | Evidence spans are validated against the referenced transcript version. |
| AC-008 | Invalid span boundaries are rejected. |
| AC-009 | The source data can be retrieved by ID and version. |
| AC-010 | Downstream components can consume the documented source contract. |
| AC-011 | Audio input and multiple-resident processing are not supported. |
| AC-012 | API validation and persistence tests run without calling an LLM. |

## Requirement and evidence-integrity traceability

| Requirement or invariant | Acceptance coverage |
| --- | --- |
| FR-01: one structured German transcript and one scalar resident test ID | AC-001, AC-004, AC-011; User Story 1 scenarios 1 and 3 |
| Exact source text preservation | AC-005; User Story 1 scenario 4 |
| Immutable `(source_id, source_version)` identity | AC-003, AC-006, AC-009; User Story 2 scenarios 1 and 3 |
| Atomic version creation and stale-write rejection | User Story 2 scenario 2; AC-012 persistence/API test requirement |
| Unicode scalar-value, inclusive/exclusive span semantics | AC-007, AC-008; User Story 3 scenarios 1 and 2 |
| Source/version existence before evidence resolution | AC-007, AC-009; User Story 3 scenario 3 |
| No silent cross-version evidence redirection | User Story 3 scenario 4 |
| No LLM dependency for validation or persistence | AC-012; User Story 1 and 2 independent tests |

## Verification requirements

The implementation is complete when automated tests demonstrate:

1. valid German text is accepted and persisted;
2. blank, malformed, non-text, unsupported, and structurally invalid requests fail with structured errors;
3. source IDs are unique and source/version identity is stable;
4. the stored transcript round-trips byte-for-byte or, for the selected runtime representation, character-for-character;
5. prior versions remain retrievable after a newer version is accepted;
6. valid spans resolve only within their referenced version;
7. zero-length, reversed, negative, out-of-range, missing-source, missing-version, and cross-version spans fail;
8. dependent components can construct and consume the documented source references without importing an LLM client.

Tests must use deterministic fixtures and fakes or in-memory persistence where appropriate. No test for this specification may require an LLM provider, network access to an LLM service, medical judgment, audio processing, multi-resident resolution, or production authentication.

## Implementation boundary

This specification is intentionally narrow enough to implement independently. Future specifications may build note, fact, claim, evidence, review, and evaluation behavior on these contracts, but they must preserve the source ID, version, transcript immutability, and span validation rules established here.
