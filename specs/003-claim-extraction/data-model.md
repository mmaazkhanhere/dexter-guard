# Data Model: Claim and Source Fact Extraction

**Feature ID:** 003-claim-and-source-fact-extraction  
**Status:** Normative contract for Spec 003  
**Serialization:** Pydantic v2 models; JSON uses camelCase aliases. Decimal values serialize as strings, never binary floats.

## Contract boundary

Spec 003 creates claims from the immutable candidate nursing-note revision. It records candidate-note provenance and the immutable reference that Spec 004 must later use for transcript verification. It does not add transcript evidence or any support, contradiction, diagnosis, severity, or approval result.

## Shared value objects

### `EvidenceSourceReference`

| Field | Required | Constraint |
| --- | --- | --- |
| `sourceId` | Yes | Non-empty stable source-document identifier. |
| `sourceVersion` | Yes | Positive integer identifying the immutable source version. |
| `sourceTextHash` | Yes | Non-empty hash of the exact source body for that version. |
| `normalizationPolicy` | Yes | Versioned source-offset/normalization policy identifier. |

This reference comes from immutable note-revision metadata. It is a verification input, not proof that a claim is supported.

### `residentTestId`

Every Spec 003 input carries the single non-empty synthetic `residentTestId` from immutable note/source metadata. Extraction does not identify, infer, or disambiguate residents. A missing or mismatched test ID is a typed failure.

### `TextSpan`

| Field | Required | Constraint |
| --- | --- | --- |
| `startCodePoint` | Yes | Zero-based, `>= 0`. |
| `endCodePointExclusive` | Yes | End-exclusive, greater than start. |
| `startUtf16` | Yes | Zero-based, `>= 0`. |
| `endUtf16Exclusive` | Yes | End-exclusive, greater than start. |
| `text` | Yes | Non-empty exact substring. |

Spans resolve against the immutable stored candidate-note body: UTF-8 text stored without post-storage normalization. Both coordinate systems must select exactly `text`. Browser UTF-16 coordinates are supplementary; code-point coordinates are the canonical backend location.

### `NumericValue`

| Field | Required | Constraint |
| --- | --- | --- |
| `raw` | Yes | Exact note substring, including sign/approximation marker. |
| `normalizedDecimal` | No | Pydantic `Decimal`; serialized as a decimal string only for direct, unambiguous normalization. |
| `unitRaw` | No | Exact stated unit text. |
| `unitNormalized` | No | Only a directly unambiguous canonical unit; never inferred. |
| `approximation` | Yes | `true` only if explicitly marked in the note. |
| `range` | No | `{ lower: Decimal, upper: Decimal }`, serialized as strings; no range expansion. |
| `valueSpan` | Yes | Exact value substring. |
| `unitSpan` | No | Exact unit substring. |

`raw` is authoritative. Decimal-comma normalization changes representation only; no conversion, rounding, missing-unit inference, or precision loss is allowed.

## Claim model

### Enums

| Enum | Values |
| --- | --- |
| `ClaimCategory` | `OBSERVATION`, `SYMPTOM`, `MEASUREMENT`, `VITAL_SIGN`, `MEDICATION`, `CARE_ACTION`, `FUNCTION`, `ELIMINATION`, `NUTRITION_HYDRATION`, `SLEEP`, `BEHAVIOUR`, `EVENT`, `CLINICAL_CONCLUSION`, `OTHER` |
| `Polarity` | `AFFIRMED`, `NEGATED`, `UNKNOWN` |
| `Certainty` | `CERTAIN`, `UNCERTAIN`, `POSSIBLE`, `UNKNOWN` |
| `Attribution` | `CARE_RECIPIENT`, `CAREGIVER`, `THIRD_PARTY`, `DOCUMENT_AUTHOR`, `UNSPECIFIED` |

### `Claim`

| Field | Required | Constraint |
| --- | --- | --- |
| `id` | Yes | Unique within one extraction result; stable only within its note revision/result. |
| `noteRevisionId` | Yes | Exact immutable candidate-note revision. |
| `residentTestId` | Yes | Single non-empty synthetic test ID from immutable metadata. |
| `ordinal` | Yes | Positive, deterministic order within result. |
| `category` | Yes | `ClaimCategory`. `CLINICAL_CONCLUSION` does not imply validity. |
| `statementSpan`, `claimText` | Yes | `claimText == statementSpan.text`. |
| `subject`, `predicate`, `object` | No | Omit rather than invent missing structure. |
| `polarity`, `negationCue` | Yes / No | `NEGATED` requires a direct cue span; no implicit negation. |
| `certainty`, `certaintyCue` | Yes / No | Preserve direct uncertainty cue where present. |
| `attribution`, `attributionText`, `attributionSpan` | Yes / No | Non-`UNSPECIFIED` attribution needs textual evidence. |
| `temporalText`, `temporalSpan` | No | Directly stated temporal context only. |
| `numericValues` | Yes | May be empty; all entries satisfy `NumericValue`. |
| `medication` | No | Directly stated name, dose, route, and administration timing only. |
| `extractionWarnings` | Yes | Non-fatal, machine-readable warning codes; warnings cannot repair invalid output. |

Nested cue/value spans must resolve exactly and lie inside the statement span unless their documented overlap is necessary for independently addressable claims.

## Extraction-result union

All result variants include `extractionRunId`, `extractorVersion`, `outputSchemaVersion`, and `extractedAt`. Provider/model/prompt versions are included when a provider was invoked. `extractionRunId` is idempotent for one attempt and distinct from a verification run.

| Variant | Required fields | Forbidden fields |
| --- | --- | --- |
| `ExtractionSucceeded` | `status=SUCCEEDED`, `noteRevisionId`, `noteBodyHash`, `evidenceSourceReference`, one or more `claims` | `error` |
| `ExtractionEmpty` | `status=EMPTY`, `noteRevisionId`, `noteBodyHash`, `evidenceSourceReference`, `claims=[]` | `error` |
| `ExtractionFailed` | `status=FAILED`, `claims=[]`, typed `error`; revision/body hash may be absent only when resolution failed | `evidenceSourceReference` when no revision resolved |

`ExtractionError.code` is one of:

`MALFORMED_PROVIDER_OUTPUT | INVALID_SCHEMA | INVALID_SPAN | REVISION_NOT_FOUND | REVISION_MISMATCH | UNSUPPORTED_LANGUAGE | NON_SYNTHETIC_INPUT | REQUEST_TOO_LARGE | PROVIDER_TIMEOUT | PROVIDER_UNAVAILABLE | INTERNAL_VALIDATION_ERROR`

Every error also has a non-sensitive `message` and `retryable` boolean. Pydantic discriminated-union validation rejects any invalid variant, including a failed result without an error or a successful result with one.

## Verification handoff boundary

`ClaimExtractionService.get_current_result(note_revision_id)` returns the immutable successful/empty result record, including note provenance and carried `EvidenceSourceReference`. Spec 004 consumes that typed result before a revision becomes verification-ready. No asynchronous event delivery, outbox, evidence alignment, or evidence verdict is required by this PoC.

## Persistence model

| Record | Required fields |
| --- | --- |
| `claim_extraction_result` | result id, extraction run id, revision id, note body hash, evidence source reference, extractor/provider/model/prompt/schema versions, discriminated status/error, timestamps |
| `claim` | id, result id, ordinal, semantic fields, exact spans, raw values, warnings |

Use one SQLite transaction for a successful/empty result, its claims, and append-only provenance record. A failed result persists no claims but retains its append-only run/error record. New note revisions never reuse an older extraction result or claim identity.

## Cross-model invariants

1. Every returned/persisted span matches the immutable note body exactly in both coordinate systems.
2. Every claim belongs to the exact result revision and has a unique id/ordinal within that result.
3. Every successful/empty result carries immutable source-reference metadata and is retrievable through the typed service/persisted record for Spec 004.
4. No Spec 003 model contains an evidence verdict, transcript span, diagnosis, approval state, or severity decision.
5. Request note bodies over 50,000 Unicode code points fail with `REQUEST_TOO_LARGE` before a provider call.
