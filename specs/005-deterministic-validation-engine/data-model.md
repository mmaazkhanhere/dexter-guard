# Spec 005 — Versioned Data Model

**Domain contract version:** `DVE-CONTRACT-v1`  
**Ruleset version:** `DVE-RULESET-v1`

## Core records

| Record | Required fields | Invariants |
| --- | --- | --- |
| `TranscriptSnapshot` | `source_id`, positive `source_version`, `transcript_text` | Text is exact immutable Spec 001 text. |
| `EvidenceReference` | stable `evidence_reference_id`, source identity, `start`, `end`, `quoted_text` | ID is unique within a run; span is non-empty and uses Unicode code-point offsets. |
| `Measurement` | `category`, typed `value`, `unit`, `approximation` | Scalar or typed BP value; no raw-text inference. |
| `SourceFact` | `source_fact_id`, source identity, `measurement`, evidence references | Source identity equals validation run snapshot. |
| `Claim` | `claim_id`, `note_id`, nullable `note_revision`, `measurement`, evidence references | Missing/null revision is reported as `STR-002`; a non-null mismatch is provenance failure. |
| `Alignment` | `alignment_id`, `source_fact_id`, `claim_id`, `status` | Each record is one comparison pair; fact/claim IDs may recur across different pairs. |
| `ValidationFinding` | catalog metadata, outcome, source/claim/alignment/evidence-reference IDs, expected/observed/unit, reason, review flag | Expected/observed/unit are always present and nullable; conditional non-null/reference rules are DVE-011. |
| `ValidationRun` | run ID, source identity, note ID/revision, input digest, engine/ruleset/contract version, ordered results | Records immutable run binding and all output findings/outcomes. |
| `ApiError` | stable code, safe message, optional correlation ID | Returned for non-successful resolution or execution; never contains a partial run/findings payload. |

## Enumerations

```text
AlignmentStatus = ALIGNED | UNAVAILABLE | AMBIGUOUS | REJECTED
Outcome         = PASS | FAIL | NOT_EVALUABLE
Approximation   = EXACT | APPROXIMATE | UNSPECIFIED
Category        = TEMPERATURE | PULSE | FLUID_INTAKE | MEDICATION_QUANTITY | BLOOD_PRESSURE
Unit            = CELSIUS | BEATS_PER_MINUTE | MILLILITRE | LITRE | MILLIGRAM | GRAM | MMHG
```

`ALIGN-001` is the rule result for a non-`ALIGNED` `AlignmentStatus`; it is not a semantic evidence classification. Alignments are preselected comparison pairs, not a claim-coverage assertion or a semantic lookup request.

## Category and unit policy

| Category | Accepted v1 units | Canonical unit | Value shape |
| --- | --- | --- | --- |
| `TEMPERATURE` | `CELSIUS` | `CELSIUS` | exact decimal scalar |
| `PULSE` | `BEATS_PER_MINUTE` | `BEATS_PER_MINUTE` | exact decimal scalar |
| `FLUID_INTAKE` | `MILLILITRE`, `LITRE` | `MILLILITRE` | exact decimal scalar |
| `MEDICATION_QUANTITY` | `MILLIGRAM`, `GRAM` | `MILLIGRAM` | exact decimal scalar |
| `BLOOD_PRESSURE` | `MMHG` | `MMHG` | `{ systolic: positive integer, diastolic: positive integer }` |

Conversion uses `Decimal`: `1 L = 1000 ml`; `1 g = 1000 mg`. Scalar `value` is a decimal text representation accepted by DVE-002; a non-parseable string is permitted at the contract boundary so `STR-001` can report it. Blood-pressure `value` is an object with exactly `systolic` and `diastolic` integer-or-text components; each component must parse as a positive integer, otherwise `STR-001` is emitted. Values are not rounded, clinically ranged, or inferred. The raw display value may be retained for review but cannot drive comparison.

## Result semantics

- `PASS`: an internal rule was evaluated and found no discrepancy. `PASS` is not a public `ValidationFinding` outcome; public reviewer responses omit pass records.
- `FAIL`: a rule found an objective discrepancy or structural/evidence error. `requires_review=true`.
- `NOT_EVALUABLE`: rule prerequisites are absent or unsafe. It is an explicit non-pass, contains a reason code, and does not claim contradiction.

An invalid request envelope does not create a partial `ValidationRun`; it is rejected using the stable `SCHEMA_ERROR` envelope. A resolved persisted claim with a missing/null `note_revision` creates `STR-002`; a resolved claim whose note identity conflicts with the run is `PROVENANCE_CONFLICT`. Missing records, dependency failures, and unexpected failures return the API error contract and never a partial `ValidationRun`.
