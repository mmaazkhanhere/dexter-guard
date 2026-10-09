# Data Model: Source and Note Ingestion

## Purpose

This document defines the persistent data model for Spec 001. It covers the immutable source document version and the reusable evidence span used by downstream components.

Spec 001 does not define the complete data models for `NursingNote`, `SourceFact`, `Claim`, `EvidenceFinding`, `ReviewDecision`, or `EvaluationCase`. Those contracts may reference the source model defined here.

## Identity model

The authoritative identity of a transcript version is the composite key:

```text
(source_id, source_version)
```

- `source_id` identifies a logical source document.
- `source_version` identifies one immutable version of that source document.
- Every initial transcript submission creates a new unique `source_id` at version `1`.
- A revision must explicitly create the next version for an existing `source_id`.
- Existing versions are never silently overwritten or deleted by ingestion.

## SourceDocument

`SourceDocument` represents one immutable version of one German nursing transcript concerning one synthetic resident.

### Fields

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `source_id` | string | Yes | Globally unique logical source identifier. Stable across versions. |
| `source_version` | positive integer | Yes | Starts at `1`; unique within `source_id`. |
| `resident_test_id` | string | Yes | Exactly one synthetic resident test identifier; non-blank and schema-valid. |
| `language` | string | Yes | Must be `de-DE` for this proof of concept. |
| `transcript_text` | string | Yes | Non-blank original text. Must be persisted unchanged. |
| `created_at` | timestamp | Yes | Time at which this immutable version was accepted. |

### Example

```json
{
  "source_id": "src_01J8GERMAN001",
  "source_version": 1,
  "resident_test_id": "resident-test-001",
  "language": "de-DE",
  "transcript_text": "Frau Müller berichtet über unruhigen Schlaf.\nDie Pflegekraft beobachtet Müdigkeit.",
  "created_at": "2026-10-09T12:00:00Z"
}
```

The example text is illustrative only. Implementations must preserve the submitted text exactly, including whitespace, punctuation, casing, line breaks, and non-ASCII characters.

## SourceSpan

`SourceSpan` is a reusable value object that points to an exact character range in one immutable `SourceDocument` version.

### Fields

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `source_id` | string | Yes | Must identify an existing source. |
| `source_version` | positive integer | Yes | Must identify an existing version of `source_id`. |
| `start` | non-negative integer | Yes | Inclusive, zero-based character offset. |
| `end` | non-negative integer | Yes | Exclusive, zero-based character offset. |

### Span invariant

For the exact transcript identified by `(source_id, source_version)`:

```text
0 <= start < end <= character_length(transcript_text)
```

This means:

- spans cannot be empty;
- spans cannot be reversed;
- spans cannot begin before the transcript;
- spans cannot end after the transcript;
- the source and version must exist before the span can be resolved.

The implementation must use one documented character-offset convention consistently across API responses, persistence, validation, and tests. `start` is inclusive and `end` is exclusive.

### Resolved span

A resolved span may expose a derived excerpt for display or downstream processing:

```json
{
  "source_id": "src_01J8GERMAN001",
  "source_version": 1,
  "start": 0,
  "end": 27,
  "text": "Frau Müller berichtet über"
}
```

The derived `text` is not authoritative by itself. Consumers must retain the source ID, source version, and boundaries.

## Relationships

```text
SourceDocument (source_id, source_version)
        │
        ├── referenced by SourceSpan
        ├── referenced by NursingNote revisions
        ├── referenced by SourceFact
        ├── indirectly referenced by Claim
        ├── referenced by EvidenceFinding
        ├── referenced by ReviewDecision artifacts
        └── used as the source contract for EvaluationCase inputs
```

Downstream records must reference the composite source identity. A source ID without a version is insufficient for evidence-bearing references.

## Persistence model

The persistence layer must provide a source-version record keyed by:

```text
primary key = (source_id, source_version)
```

It must support:

1. creating a new source at version `1`;
2. creating the next version for an existing source;
3. retrieving one exact source version;
4. checking source/version existence for span validation;
5. preserving all historical versions;
6. rejecting duplicate source/version keys;
7. returning the original transcript text without normalization.

An implementation may use an in-memory repository for the proof of concept or the project's existing persistence technology, provided these behaviors remain stable behind a repository interface.

## Immutability rules

After persistence:

- `transcript_text` cannot be edited in place;
- `resident_test_id` cannot be changed for an existing version;
- `language` cannot be changed for an existing version;
- `source_id` and `source_version` cannot be reassigned;
- a correction creates a new source version;
- all spans continue to refer to the exact version for which they were created.

## Validation rules

### SourceDocument validation

Reject a source document when:

- the transcript is missing, non-text, blank, or whitespace-only;
- the resident test ID is missing, blank, malformed, or not exactly one ID;
- the language is unsupported;
- the request is structurally malformed;
- the source/version identity would collide with an existing record.

Validation checks input format and schema only. It does not determine whether caregiver observations are medically accurate.

### SourceSpan validation

Reject a span when:

- `source_id` is missing or unknown;
- `source_version` is missing or unknown;
- `start` or `end` is missing or not an integer;
- `start` or `end` is negative;
- `start >= end`;
- `end` exceeds the character length of the referenced transcript version;
- the span was calculated against a different source version.

## Error data

Validation and lookup failures should use a stable structured shape:

```json
{
  "code": "INVALID_SOURCE_SPAN",
  "message": "The span end offset exceeds the referenced transcript version.",
  "field": "end"
}
```

Recommended source-related error codes:

| Code | Meaning |
| --- | --- |
| `INVALID_REQUEST` | Structured request is malformed. |
| `INVALID_TRANSCRIPT` | Transcript is missing, non-text, blank, or unsupported. |
| `INVALID_RESIDENT_TEST_ID` | Resident identifier is missing or invalid. |
| `UNSUPPORTED_INPUT_TYPE` | Audio or another unsupported input type was submitted. |
| `SOURCE_NOT_FOUND` | `source_id` does not exist. |
| `SOURCE_VERSION_NOT_FOUND` | Version does not exist for the source. |
| `DUPLICATE_SOURCE_VERSION` | Source/version identity already exists. |
| `INVALID_SOURCE_SPAN` | Span boundaries or reference are invalid. |

## Contract stability requirements

Downstream specifications may add domain-specific fields, but they must preserve:

- `source_id`;
- `source_version`;
- the immutable transcript semantics;
- the `SourceSpan` offset convention;
- source/version validation before evidence is consumed.

No data model in this specification may require an LLM provider, medical reasoning, audio processing, multi-resident disambiguation, or production authentication.
