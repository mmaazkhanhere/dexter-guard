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
| `Claim` | `claim_id`, `note_id`, positive `note_revision`, `measurement`, evidence references | Claim is immutable upstream data. |
| `Alignment` | `alignment_id`, `source_fact_id`, `claim_id`, `status` | Every submitted fact and claim appears exactly once; only `ALIGNED` is comparable. |
| `ValidationFinding` | catalog metadata, outcome, source/claim/alignment/evidence-reference IDs, reason, severity, review flag | `evidence_reference_ids` is always present; a `FAIL` or `NOT_EVALUABLE` is retained; pass trace is optional. |
| `ValidationRun` | run ID, source identity, ruleset/contract version, ordered results | Records input digest and all output findings/outcomes immutably. |

## Enumerations

```text
AlignmentStatus = ALIGNED | UNAVAILABLE | AMBIGUOUS | REJECTED
Outcome         = PASS | FAIL | NOT_EVALUABLE
Approximation   = EXACT | APPROXIMATE | UNSPECIFIED
Category        = TEMPERATURE | FLUID_INTAKE | MEDICATION_QUANTITY | BLOOD_PRESSURE
Unit            = CELSIUS | MILLILITRE | LITRE | MILLIGRAM | GRAM | MMHG
```

`ALIGN-001` is the rule result for a non-`ALIGNED` `AlignmentStatus`; it is not a semantic evidence classification.

## Category and unit policy

| Category | Accepted v1 units | Canonical unit | Value shape |
| --- | --- | --- | --- |
| `TEMPERATURE` | `CELSIUS` | `CELSIUS` | exact decimal scalar |
| `FLUID_INTAKE` | `MILLILITRE`, `LITRE` | `MILLILITRE` | exact decimal scalar |
| `MEDICATION_QUANTITY` | `MILLIGRAM`, `GRAM` | `MILLIGRAM` | exact decimal scalar |
| `BLOOD_PRESSURE` | `MMHG` | `MMHG` | `{ systolic: positive integer, diastolic: positive integer }` |

Conversion uses `Decimal`: `1 L = 1000 ml`; `1 g = 1000 mg`. Scalar `value` is a decimal text representation accepted by DVE-002; a non-parseable string is permitted at the contract boundary so `STR-001` can report it. Blood-pressure `value` is an object with exactly `systolic` and `diastolic` integer-or-text components; any text component must parse as an integer or `STR-001` is emitted. Values are not rounded, ranged, or inferred. The raw display value may be retained for review but cannot drive comparison.

## Result semantics

- `PASS`: a rule was evaluated and found no discrepancy. Default reviewer responses omit pass records.
- `FAIL`: a rule found an objective discrepancy or structural/evidence error. `requires_review=true`.
- `NOT_EVALUABLE`: rule prerequisites are absent or unsafe. It is an explicit non-pass, contains a reason code, and does not claim contradiction.

An invalid request envelope does not create a partial `ValidationRun`; it is rejected using the stable `SCHEMA_ERROR` envelope. Once a run has valid identity, individual malformed data may yield findings as the contract permits.
