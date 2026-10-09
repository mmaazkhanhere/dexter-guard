# Spec 001: Source and Note Ingestion

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
- a submission that does not represent exactly one resident;
- unsupported audio or other non-text input;
- malformed structured requests.

Validation failures use a structured error shape with a stable error code, a human-readable message, and the field or path that failed when applicable. Validation must be deterministic and must not call an LLM.

Validation does not assess whether the transcript's observations are medically accurate.

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

Valid spans satisfy `0 <= start < end <= character_length(transcript)`. The referenced source ID and version must exist, and the boundaries must be valid for that exact transcript version. Invalid, reversed, empty, out-of-range, or cross-version spans are rejected.

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

The source identity is the pair `(source_id, source_version)`. Every initial submission creates a new unique `source_id` at `source_version = 1`. A later revision is allowed only through an explicit versioned operation for that `source_id`, which creates the next version and preserves every prior version. A normal submission must never overwrite an existing source or version.

### `SourceSpan`

`SourceSpan` is the reusable evidence-reference value object owned by this specification. It must identify the exact source version and a valid character range within that version.

Required fields:

| Field | Type | Requirements |
| --- | --- | --- |
| `source_id` | string | Must identify an existing source. |
| `source_version` | version value | Must identify an existing version of `source_id`. |
| `start` | non-negative integer | Inclusive character offset. |
| `end` | positive integer | Exclusive character offset; must be greater than `start`. |

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

## Error contract

All rejected requests use a structured error response with:

- a stable machine-readable `code`;
- a human-readable `message`;
- a `field` or `path` when the failure is tied to an input location.

At minimum, the implementation should distinguish blank or invalid transcript input, invalid resident ID, unsupported input type, malformed request, source not found, version not found, and invalid source span.

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
