# Tasks: Source and Note Ingestion

## Contract and schema

- [ ] Define the `SourceDocument` contract with source ID, version, resident test ID, language, transcript text, and creation timestamp.
- [ ] Define the `SourceSpan` value object with source ID, source version, inclusive start, and exclusive end offsets.
- [ ] Document the zero-based character-offset convention.
- [ ] Document the immutable source/version identity `(source_id, source_version)`.
- [ ] Add contract fixtures usable by downstream specifications.

## Validation

- [ ] Validate that the request is structurally well formed.
- [ ] Validate that transcript input is text.
- [ ] Reject missing, blank, and whitespace-only transcripts.
- [ ] Validate a single synthetic `resident_test_id`.
- [ ] Enforce `language = de-DE` for this proof of concept.
- [ ] Reject unsupported audio and other non-text input.
- [ ] Reject multi-resident submissions according to the selected request schema.
- [ ] Return stable structured validation errors with code, message, and field/path.
- [ ] Ensure invalid submissions do not create partial persistence records.

## Identification and versioning

- [ ] Generate a unique source ID for every initial accepted transcript.
- [ ] Start each new source at version 1.
- [ ] Implement an explicit operation for creating the next version of an existing source.
- [ ] Preserve every previous source version without overwriting.
- [ ] Reject duplicate source/version identities.
- [ ] Keep the resident test ID stable across versions of the same source.

## Persistence and retrieval

- [ ] Add a repository abstraction for source documents.
- [ ] Persist the exact original transcript text.
- [ ] Support retrieval by `source_id` and `source_version`.
- [ ] Return a structured not-found error for missing sources and versions.
- [ ] Verify that retrieval returns the stored text without normalization or correction.

## Source spans

- [ ] Validate that the referenced source exists.
- [ ] Validate that the referenced source version exists.
- [ ] Reject negative offsets.
- [ ] Reject zero-length spans.
- [ ] Reject reversed spans.
- [ ] Reject end offsets beyond the exact transcript version.
- [ ] Reject cross-version or stale references.
- [ ] Resolve valid spans as derived excerpts while retaining the authoritative source reference.

## API/demo integration

- [ ] Expose new transcript submission through the existing demo/API convention.
- [ ] Expose explicit source-version creation.
- [ ] Expose source retrieval by ID and version.
- [ ] Expose source-span validation or resolution.
- [ ] Return source identity and version in successful responses.
- [ ] Return structured errors for all documented rejection cases.

## Tests

- [ ] Add a valid German transcript acceptance test.
- [ ] Add blank and whitespace-only transcript tests.
- [ ] Add malformed request and non-text input tests.
- [ ] Add unique source ID tests.
- [ ] Add exactly-one-resident association tests.
- [ ] Add exact text round-trip tests using German characters and line breaks.
- [ ] Add version preservation and historical retrieval tests.
- [ ] Add valid source-span tests.
- [ ] Add invalid span boundary tests.
- [ ] Add missing source/version tests.
- [ ] Add audio and multi-resident exclusion tests.
- [ ] Verify the test suite runs without an LLM provider or network call.

## Scope guard

- [ ] Confirm no LLM SDK, provider, prompt, or medical reasoning is required by this specification.
- [ ] Confirm no speech recognition or audio pipeline is introduced.
- [ ] Confirm no multi-resident disambiguation is introduced.
- [ ] Confirm no production authentication or authorization is introduced.
- [ ] Confirm domain-specific fields for notes, facts, claims, findings, reviews, and evaluation cases remain owned by their respective specifications.
