# Implementation Plan: Source and Note Ingestion

## Objective

Implement the smallest reliable foundation for accepting, validating, identifying, versioning, persisting, retrieving, and referencing one German nursing transcript for one synthetic resident.

## Design principles

- Treat accepted transcript text as immutable source evidence.
- Make `(source_id, source_version)` the stable identity of a source version.
- Preserve the exact submitted text, including whitespace, punctuation, casing, line breaks, and German characters.
- Keep schema validation separate from medical or semantic judgment.
- Keep source contracts independent of LLM providers.
- Make source spans explicit and validate them against the exact referenced version.
- Keep implementation narrow enough to test without external services.

## Ownership

### In scope

- `SourceDocument` contract and persistence model.
- `SourceSpan` value object and boundary validation.
- Transcript submission and structured validation errors.
- Unique source ID generation.
- Explicit source-version creation and retrieval.
- In-memory or repository-backed persistence using the project's existing conventions.
- API/demo behavior and deterministic tests.

### Out of scope

- Full `NursingNote`, `SourceFact`, `Claim`, `EvidenceFinding`, `ReviewDecision`, or `EvaluationCase` behavior.
- Medical accuracy checking or clinical reasoning.
- LLM integration, prompts, or model selection.
- Audio input and speech recognition.
- Multi-resident disambiguation.
- Production authentication and authorization.

## Source identity and version policy

1. A new transcript submission creates a new globally unique `source_id` at `source_version = 1`.
2. A revision must use an explicit versioned operation for an existing `source_id`.
3. The revision receives the next version and preserves all prior versions.
4. Existing source versions are never updated or deleted by ingestion.
5. Every evidence reference must include both `source_id` and `source_version`.

## Contract design

### SourceDocument

Required fields:

| Field | Rule |
| --- | --- |
| `source_id` | Globally unique and stable. |
| `source_version` | Positive version value; starts at 1. |
| `resident_test_id` | Exactly one non-blank synthetic resident identifier. |
| `language` | `de-DE` for this proof of concept. |
| `transcript_text` | Non-blank original text, unchanged. |
| `created_at` | Timestamp assigned at persistence. |

The persisted record is immutable after creation.

### SourceSpan

Required fields:

| Field | Rule |
| --- | --- |
| `source_id` | Existing source identifier. |
| `source_version` | Existing version of that source. |
| `start` | Zero-based inclusive character offset. |
| `end` | Zero-based exclusive character offset. |

Valid spans satisfy `0 <= start < end <= character_length(transcript_text)` for the exact referenced version.

## Validation behavior

Reject submissions with:

- missing, blank, or non-text transcript;
- missing, blank, or malformed `resident_test_id`;
- missing required request fields;
- malformed structured payloads;
- unsupported audio or other non-text input;
- a request representing more than one resident.

Validation returns a structured error containing a stable `code`, readable `message`, and applicable `field` or `path`. No invalid request creates a partial persisted record.

Span validation rejects:

- missing source or version;
- negative offsets;
- `start >= end`;
- end offsets beyond the referenced transcript;
- spans that refer to a non-existent source/version;
- references resolved against a different transcript version.

## API surface

The transport may follow existing repository conventions, but the behavior must expose equivalent operations:

1. Submit a new transcript.
2. Create the next version for an existing source ID.
3. Retrieve a source by ID and version.
4. Validate or resolve a source span.

Successful submission and retrieval responses expose the source ID, version, synthetic resident ID, language, transcript text, and creation metadata as appropriate. Errors are deterministic and do not invoke an LLM.

## Persistence approach

Use the repository's existing persistence abstraction if one exists. Otherwise, start with a deterministic in-memory repository behind an interface so it can be replaced without changing the contracts.

The repository must support:

- create initial source version;
- create next source version;
- retrieve exact source/version;
- verify source/version existence;
- preserve insertion history without overwriting records;
- reject duplicate source/version identity.

## Testing strategy

Tests should use fixed German fixtures and deterministic ID/time providers where possible. They must not call an LLM or require network access.

Required test groups:

1. Valid submission and response contract.
2. Blank, malformed, non-text, unsupported, and structurally invalid input.
3. Unique source ID generation.
4. Exactly one synthetic resident association.
5. Exact transcript round-trip, including non-ASCII characters and line breaks.
6. Version creation, preservation, and retrieval of older versions.
7. Valid span resolution.
8. Negative, empty, reversed, out-of-range, missing-source, missing-version, and cross-version span rejection.
9. Downstream construction of source-linked references without an LLM dependency.

## Acceptance mapping

| Criterion | Planned verification |
| --- | --- |
| AC-001 | Submission integration test with valid German fixture. |
| AC-002 | Blank and whitespace-only validation tests. |
| AC-003 | Repeated submission test asserting unique IDs. |
| AC-004 | Request/schema tests requiring exactly one synthetic resident ID. |
| AC-005 | Exact persistence round-trip test. |
| AC-006 | Versioning test retrieving both old and new versions. |
| AC-007 | Span resolution test against the selected version. |
| AC-008 | Boundary matrix tests. |
| AC-009 | Retrieval-by-ID-and-version test. |
| AC-010 | Contract fixture/import test for downstream consumers. |
| AC-011 | Unsupported audio and multi-resident rejection tests. |
| AC-012 | Test configuration proving no LLM provider is required. |

## Completion definition

Implementation is complete when the contracts are documented, the API/demo supports the required operations, persistence preserves immutable source versions, span validation is version-aware, and all in-scope tests pass without an LLM provider.
