# Feature Specification: Claim and Source Fact Extraction

**Feature ID:** 003-claim-and-source-fact-extraction  
**Status:** Draft for requirements review  
**Primary requirement:** FR-06 — extract atomic claims from candidate notes  
**Constitution baseline:** AI Nursing Documentation Reliability Engine Constitution v1.0.0  
**Upstream:** Spec 002 — Nursing Note Generation  
**Downstream:** Specs 004, 005, and 007

## Purpose

Convert a generated or externally imported German nursing note into structured, individually addressable factual claims. This feature records what the candidate note says; it does not decide whether any statement is true, supported by a caregiver transcript, clinically appropriate, or contradicted by a source.

For example, if a note states `Temperatur 37,8 °C` while a source later states 36.8 °C, this feature emits the candidate-note claim of 37.8 °C unchanged. Evidence comparison belongs to Spec 004/005.

## Scope

### In scope

- German candidate notes created by Spec 002 or imported from another source.
- Identification of factual assertions and decomposition into atomic claims.
- Preservation of wording-dependent semantics: negation, uncertainty, attribution, numerical form, units, approximation, and temporal context.
- Exact source locations within an immutable nursing-note revision.
- Explicit success, valid-empty, and failure outcomes.
- A testable extraction service; `POST /api/v1/claims/extract` is optional as a public façade.

### Out of scope

- Retrieving, parsing, or comparing caregiver transcripts.
- Assigning supported, unsupported, contradicted, verified, risk, or diagnostic status.
- Correcting, normalizing away, or clinically interpreting a candidate-note assertion.
- Clinical diagnosis, medication safety decisions, or treatment recommendations.
- Merging claims across note revisions.

## Actors and preconditions

| Actor | Need |
|---|---|
| Note-generation/import workflow | Submit a stored note revision for claim extraction. |
| Evidence-verification workflow (Spec 004) | Address each candidate-note claim independently. |
| UI workflow (Spec 007) | Highlight a claim's exact note text. |

A request identifies one existing, immutable `noteRevisionId` and the exact stored note text for that revision. The stored body is synthetic-only, retained as immutable UTF-8 text with no normalization applied after storage; the body hash and declared language are part of the revision record. A revision is extracted independently; an edit creates a new revision and requires a new extraction before re-verification.

## Contract boundary

The output is a set of individually addressable `Claim` records associated with one immutable note revision and its already-associated source reference. Detailed field shapes, persistence records, serialization choices, and error-code enums are normative in `data-model.md`; they are not feature requirements in this specification.

Each claim carries its note-revision provenance, its note location, the source reference already associated with the note, and the semantic attributes required for downstream verification. The extractor does not locate or assess supporting source evidence.

### `ClaimCategory`

An extensible classification describing the asserted subject matter, not evidence status:

`OBSERVATION | SYMPTOM | MEASUREMENT | VITAL_SIGN | MEDICATION | CARE_ACTION | FUNCTION | ELIMINATION | NUTRITION_HYDRATION | SLEEP | BEHAVIOUR | EVENT | CLINICAL_CONCLUSION | OTHER`

`CLINICAL_CONCLUSION` means the note asserted a conclusion; it never means the conclusion is valid.

### `Polarity`

`AFFIRMED | NEGATED | UNKNOWN`

`NEGATED` applies only when the assertion itself is negated (for example, `kein Schmerz`). It must not be inferred from an omitted statement or from uncertainty.

### `Certainty`

`CERTAIN | UNCERTAIN | POSSIBLE | UNKNOWN`

The exact uncertainty expression is retained in `certaintyCue`. This enum represents the note's linguistic stance, not truth likelihood.

### `Attribution`

`CARE_RECIPIENT | CAREGIVER | THIRD_PARTY | DOCUMENT_AUTHOR | UNSPECIFIED`

`CARE_RECIPIENT` is used for resident/patient self-report. `CAREGIVER` is used for an explicitly named care observer; `DOCUMENT_AUTHOR` is only used if the note attributes the statement to its author. Attribution may be `UNSPECIFIED`; it must never be guessed from category.

### `TextSpan`

```text
TextSpan {
  startCodePoint: integer >= 0,
  endCodePointExclusive: integer > startCodePoint,
  startUtf16: integer >= 0,
  endUtf16Exclusive: integer > startUtf16,
  text: non-empty string
}
```

`text` must exactly equal the substring at both declared coordinate systems. A claim may have a broad `statementSpan` and narrower spans for cues and values. Spans may overlap; overlap does not merge claims.

### `NumericValue`

```text
NumericValue {
  raw: string,                 // e.g. "ca. 37,8"
  normalizedDecimal: decimal?, // e.g. Decimal("37.8"); serialized as a string in JSON, never float
  unitRaw: string?,            // e.g. "°C"
  unitNormalized: string?,     // e.g. "C" only when directly unambiguous
  approximation: boolean,
  range: { lower: decimal, upper: decimal }?, // serialized as strings in JSON
  valueSpan: TextSpan,
  unitSpan: TextSpan?
}
```

Normalizing a German decimal comma to `.` is representational only; `raw` remains authoritative. Pydantic uses exact `Decimal` values internally and serializes them as decimal strings at API boundaries. No conversion, rounding, range expansion, or missing-unit inference is permitted.

### `Claim`

```text
Claim {
  id: string,
  noteRevisionId: string,
  residentTestId: string,
  ordinal: integer >= 1,
  category: ClaimCategory,
  statementSpan: TextSpan,
  claimText: string,
  subject: string?,
  predicate: string?,
  object: string?,
  polarity: Polarity,
  negationCue: TextSpan?,
  certainty: Certainty,
  certaintyCue: TextSpan?,
  attribution: Attribution,
  attributionText: string?,
  attributionSpan: TextSpan?,
  temporalText: string?,
  temporalSpan: TextSpan?,
  numericValues: NumericValue[],
  medication: {
    name: string?,
    doseRaw: string?,
    routeRaw: string?,
    administrationTemporalText: string?
  }?,
  extractionWarnings: string[]
}
```

`claimText` is exactly `statementSpan.text`. `subject`, `predicate`, and `object` are optional structured aids and may be omitted rather than fabricated. Medication fields preserve directly stated details only. Each claim is individually addressable by `id` within its `noteRevisionId`.

### Extraction result

```text
ExtractionSucceeded | ExtractionEmpty {
  status: "SUCCEEDED" | "EMPTY",
  extractionRunId: string,
  noteRevisionId: string,
  noteBodyHash: string,
  evidenceSourceReference: { sourceId: string, sourceVersion: integer, sourceTextHash: string, normalizationPolicy: string },
  extractorVersion: string,
  providerVersion: string?,
  modelVersion: string?,
  promptVersion: string?,
  outputSchemaVersion: string,
  claims: Claim[],
  extractedAt: ISO-8601 timestamp
}

ExtractionFailed {
  status: "FAILED",
  extractionRunId: string,
  noteRevisionId: string?,
  noteBodyHash: string?,
  extractorVersion: string,
  providerVersion: string?,
  modelVersion: string?,
  promptVersion: string?,
  outputSchemaVersion: string,
  claims: [],
  error: {
    code: "MALFORMED_PROVIDER_OUTPUT" | "INVALID_SCHEMA" | "INVALID_SPAN" | "REVISION_NOT_FOUND" | "REVISION_MISMATCH" | "UNSUPPORTED_LANGUAGE" | "NON_SYNTHETIC_INPUT" | "REQUEST_TOO_LARGE" | "PROVIDER_TIMEOUT" | "PROVIDER_UNAVAILABLE" | "INTERNAL_VALIDATION_ERROR",
    message: string,
    retryable: boolean
  },
  extractedAt: ISO-8601 timestamp
}
```

`SUCCEEDED` requires one or more valid claims. `EMPTY` is successful only when the supplied text contains no factual assertion. `FAILED` contains no partial claims and a required typed error. Pydantic shall enforce this discriminated union: success/empty results cannot carry `error`, and failed results cannot omit it. A note revision has one current successful result for a specific extractor version; a changed revision is never silently associated with an older result.

`extractionRunId` identifies one auditable extraction attempt. It is distinct from any verification run. Cached successful/empty results are immutable for their note revision and extractor version; repeated attempts are recorded rather than silently replacing prior results.

`evidenceSourceReference` is copied from the immutable note-revision metadata and is required for every successful/empty result. It identifies the transcript version that Spec 004 must use; it does not assert that any claim is supported.

The normative field definitions and persistence invariants are in `data-model.md`. `spec.md` remains authoritative for feature behavior and acceptance conditions.

## Functional requirements

### FR-06 — atomic candidate-note claims

1. **FR-06.1:** The system shall identify every factual assertion in the supplied candidate note that can be independently checked against a source.
2. **FR-06.2:** The system shall emit one stable claim identifier per atomic assertion, scoped to the note revision.
3. **FR-06.3:** The system shall split compound text when it expresses independently verifiable facts, including coordinated observations, symptoms, measurements, actions, and conclusions.
4. **FR-06.4:** The system shall not split grammar alone when the fragments do not express independent factual assertions.
5. **FR-06.5:** The system shall preserve overlap when one textual phrase supports several independently addressable claims.

### Semantic-fidelity requirements

1. **SEM-003-01:** The system shall preserve negation and its local scope. It shall not turn `kein Fieber` into an affirmed fever claim.
2. **SEM-003-02:** The system shall preserve uncertainty and the exact cue where present, including expressions such as `möglicherweise`, `unklar`, and `Verdacht auf`.
3. **SEM-003-03:** The system shall preserve attribution, distinguishing a resident report (for example, `Bewohnerin berichtet`) from an explicit caregiver observation (for example, `Pflegekraft beobachtet`).
4. **SEM-003-04:** The system shall preserve numerical strings, units, signs, ranges, and approximation markers exactly. German decimals may additionally be represented with a normalized decimal point.
5. **SEM-003-05:** The system shall preserve stated temporal context and may not infer a date, duration, sequence, or recurrence that is absent.
6. **SEM-003-06:** The system shall extract a stated clinical conclusion as a claim without treating it as valid or evidence-backed.
7. **SEM-003-07:** The system shall preserve medication names and directly stated administration details without inferring indication, dose, route, frequency, or completion.
8. **SEM-003-08:** The system shall carry the single required synthetic `residentTestId` from immutable note/source metadata. It shall not infer, identify, or disambiguate residents from note wording; a missing association is an explicit failure.

### Location and revision requirements

1. **LOC-003-01:** Every claim and every present semantic cue/value span shall reference the submitted `noteRevisionId` and the exact stored note substring.
2. **LOC-003-02:** The system shall validate each span against the stored note before returning or persisting a result.
3. **LOC-003-03:** An extraction request for an altered note body or obsolete revision shall fail explicitly rather than reuse prior claims.
4. **LOC-003-04:** A newly edited note revision shall require a new extraction result before it is presented for downstream verification.
5. **HOF-003-01:** Every `SUCCEEDED` or `EMPTY` extraction result shall be available to Spec 004 through the typed extraction service or persisted result record, together with its note and source provenance. Spec 004 shall consume that result before any approval workflow can regard the revision as verification-ready.

### Failure and boundary requirements

1. **FAIL-003-01:** If structured model output is malformed, schema-invalid, contains invalid spans, conflicts with the stored note, or cannot be safely recovered, the system shall return `FAILED` with an explicit error code and no claims.
2. **FAIL-003-02:** The system shall not silently invent a subject, measurement, unit, attribution, certainty, temporal detail, resident identity, or fact to compensate for ambiguous/malformed input.
3. **FAIL-003-03:** The system shall return `EMPTY` rather than `FAILED` for a syntactically valid note that genuinely contains no factual assertion.
4. **FAIL-003-04:** The system shall provide a service interface independently testable without Spec 004.

## Non-functional requirements

- **NFR-003-01:** Extraction attempts, extractor/prompt/model versions, and cached results shall be immutable and auditable. Variation across repeated attempts shall be measured in regression evaluation; it is not itself an extraction failure.
- **NFR-003-02:** Cross-component contracts shall be versioned and validated. If a public HTTP endpoint is exposed, its contract shall be versioned and validated.
- **NFR-003-03:** Claims must be serializable in a versioned schema that preserves unknown future categories without breaking consumers.
- **NFR-003-04:** Only synthetic data may be used in requests, fixtures, logs, screenshots, demonstrations, and evaluations for this PoC.
- **NFR-003-05:** Logging/telemetry shall record only redacted run metadata, latency, cost/token usage where applicable, rejection reason codes, and warning counts; it shall not log note, prompt, claim, or transcript content.
- **NFR-003-06:** Provider calls shall use defined timeouts, bounded retries, and idempotent `extractionRunId` behavior; timeout or unavailable-provider outcomes are explicit failures.
- **NFR-003-07:** The service must make no network call to source evidence systems.
- **NFR-003-08:** Spec 003 shall contribute labeled synthetic extraction cases to the shared Spec 008 benchmark. Its feature-level evaluation measures atomic-claim precision and recall, span validity, semantic-attribute accuracy, and failure handling. End-to-end verification, completeness, reviewer-workload, and system-cost metrics are owned by Spec 008.

## Acceptance scenarios

| ID | Scenario | Expected outcome |
|---|---|---|
| CLM-001 | `Bewohnerin ist wach.` | One atomic affirmed claim. |
| CLM-002 | `Bewohnerin ist wach. Sie isst Frühstück.` | Two separately addressable claims. |
| CLM-003 | `Bewohnerin ist wach und orientiert.` | Two independent claims with valid spans. |
| CLM-004 | `Kein Schmerz angegeben.` | One claim with `NEGATED` polarity and the `Kein` cue/span. |
| CLM-005 | `Möglicherweise leichte Übelkeit.` | One claim with non-certain certainty and exact cue. |
| CLM-006 | `Der Bewohner berichtet über Schwindel.` | One symptom claim attributed to `CARE_RECIPIENT`, not caregiver observation. |
| CLM-007 | `Temperatur 37,8 °C.` | One measurement/vital-sign claim whose raw value and unit are exact. |
| CLM-008 | `Temperatur 37,8 °C.` | Numeric raw form is `37,8`; normalized decimal is `37.8`, without changing raw text. |
| CLM-009 | `Hinweis auf Harnwegsinfekt.` | A clinical-conclusion claim is extracted; it has no evidence-validity field/status. |
| CLM-010 | `Bewohnerin berichtet keine Schmerzen beim Transfer.` | Independently addressable report, symptom-negation, and transfer-context claims/spans may overlap when justified; no span corruption. |
| CLM-011 | A note is edited after initial extraction. | Old claims remain tied only to old revision; latest revision has a newly extracted result. |
| CLM-012 | Model returns invalid JSON or a span that does not match text. | `FAILED`, explicit error, no partial claims persisted/returned. |
| CLM-013 | `---` (valid note body with no factual assertion). | `EMPTY`, empty claims, no failure. |
| CLM-013a | A bounded independent empty-result safeguard finds a possible assertion. | Typed extraction failure; do not return `EMPTY`. |
| CLM-014 | `Metoprolol 25 mg oral verabreicht.` | Medication name, dose, unit, route, and stated administration are preserved; no indication/frequency inferred. |
| CLM-015 | Note/source metadata has no required resident test ID. | Typed extraction failure; no resident is inferred. |
| CLM-016 | Provider call times out or is unavailable. | Typed `FAILED` result with run id; no claims; bounded retry behavior is observable. |

## Success measures

- Every claim returned by the service has a unique `id`, a valid revision reference, and validated spans.
- Acceptance scenarios CLM-001 through CLM-016 pass structural and semantic-fidelity assertions.
- No extraction output contains an evidence-verification, contradiction, support, or diagnosis field.
- Every successful/empty extraction is available to Spec 004 through the typed service or persisted record with immutable note and carried source provenance; this does not assign an evidence verdict.
- Labeled synthetic extraction cases contribute to the shared Spec 008 benchmark. Spec 003 reports atomic-claim precision/recall, span validity, semantic-attribute accuracy, and failure-handling results.
