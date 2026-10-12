# Spec 005 — Deterministic Validation Engine

**Canonical feature specification:** This `spec.md` is the authoritative behavioral specification for Spec 005.  
**Status:** Ready for reviewer requirements-quality review; implementation not started  
**Feature:** Deterministic validation of aligned numeric claims and evidence references  
**Primary requirements:** FR-11, FR-16 in [architecture.md](../../docs/architecture.md)

## Purpose

Build a rule-based validation component that detects objectively verifiable representation errors in AI-generated German nursing documentation. The engine receives immutable transcript metadata, normalized source facts, and claims that have already been reliably aligned. It validates values, units, structured fields, and evidence-reference integrity with explicit, versioned rules. It does not use an LLM to determine a result.

The engine validates consistency, not clinical truth. A temperature, intake, blood pressure, or medication quantity is compared only after a trusted upstream component has stated that the source fact and claim concern the same measurement. Spec 004 may supply that alignment. Spec 005 must never recreate semantic matching with keywords, embeddings, or an LLM.

## Scope and ownership

### In scope

- Compare aligned scalar measurements: temperature, fluid intake, and medication quantities.
- Compare aligned blood-pressure composite measurements.
- Normalize only listed compatible unit conversions and reject incompatible categories.
- Validate structured input fields, identifiers, types, required references, permitted categories, and valid category/unit pairs.
- Validate evidence span boundaries, source/version identity, and quoted-text equality against an immutable source transcript.
- Emit stable, ordered findings or explicit `NOT_EVALUABLE` outcomes with rule and rule-set versions.
- Provide contracts and fixtures consumable by the Spec 007 review UI and Spec 008 evaluation framework.

### Out of scope

| Capability | Owner or reason |
| --- | --- |
| Generate a nursing note or extract claims | Specs 002 and 003 |
| Find semantic correspondences, contradictions, unsupported statements, or meaning changes | Spec 004 |
| Infer diagnoses, plausible clinical ranges, medical falsity, or treatment recommendations | Explicitly outside the PoC |
| Resolve multiple-resident identity conflicts | Outside the PoC / upstream provenance gate |
| Correct a note, approve a note, or set clinical workflow severity policy | Spec 007 |
| Define benchmark thresholds and release metrics | Spec 008 |

## Definitions

| Term | Meaning |
| --- | --- |
| Source fact | Immutable, normalized structured observation tied to source transcript identity and evidence references. |
| Claim | Immutable normalized extracted assertion belonging to one candidate note revision. |
| Alignment | A trusted upstream record that explicitly links one source fact and one claim as the same comparable measurement. |
| Comparable | Alignment is `ALIGNED`, both values parse, categories match, and required unit semantics are available. |
| Not evaluable | A non-successful comparison outcome caused by unavailable or ambiguous comparison prerequisites; it is never a pass. |
| Finding | A traceable rule result; `FAIL` findings contain a discrepancy and `NOT_EVALUABLE` findings explain the unmet precondition. |
| Transcript identity | Exact `(source_id, source_version)` of immutable text, per Spec 001. |

## User stories and acceptance criteria

### US-1 — Faithfully compare aligned quantities (P1)

As a caregiver reviewer, I need exact differences in aligned quantities detected deterministically, so numeric transcription changes cannot be hidden by fluent prose.

1. An aligned, parseable scalar value with compatible units is converted to its canonical category unit before comparison.
2. Equal canonical values produce no warning or failure finding.
3. Unequal canonical values produce one `NUM-001` finding with source fact ID, claim ID, expected and observed values, canonical unit, message, and `requires_review=true`.
4. An aligned blood-pressure claim compares systolic and diastolic components independently and emits `NUM-005` if either differs.
5. No clinical range, diagnosis, or truth determination is inferred from a value.

### US-2 — Preserve units and explicit precision (P1)

As a reviewer, I need equivalent conversions accepted and material unit/precision changes exposed.

1. `0,5 L` and `500 ml` compare equal under `NUM-002` and do not yield a mismatch.
2. Differing unit dimensions, such as `500 ml` and `500 mg`, yield `NUM-003`; values must not be compared numerically across dimensions.
3. `NUM-004` applies only when each comparable record supplies the structured `approximation` state. A source state of `APPROXIMATE` and claim state of `EXACT` yields a precision-mismatch finding.
4. The engine must not infer approximation from `ca.`, `genau`, or any other prose token.

### US-3 — Reject malformed structured data (P1)

As an integration consumer, I need invalid payloads identified before they are mistaken for a validated comparison.

1. Required stable IDs, note revision references, source identity, category, value representation, and evidence fields are contract-validated.
2. A numeric category with non-parseable measurement text yields `STR-001` and the affected comparison is not evaluated.
3. A claim without a required note revision yields `STR-002`; request-level missing `claim_id` is rejected with a schema error before execution.
4. Invalid category/unit pairs, such as fluid intake in Celsius, yield `STR-003` and are never converted.

### US-4 — Protect evidence-reference integrity (P1)

As a reviewer, I need every evidence reference tied to the exact source snapshot and quotation, so an apparently grounded result cannot cite altered text.

1. Evidence spans use zero-based, start-inclusive, end-exclusive Unicode code-point offsets.
2. A span outside the exact transcript boundaries yields `EVD-001`.
3. A reference to another source version yields `EVD-002`.
4. Supplied quoted text unequal to the exact substring at the span yields `EVD-003`.
5. An invalid evidence reference is never represented as verified evidence or a pass.

### US-5 — Produce deterministic and consumable results (P1)

As Specs 007 and 008, I need stable findings that can be rendered, reviewed, and evaluated independently.

1. The same valid immutable input and ruleset version returns byte-for-byte equivalent normalized results, except a caller-supplied run identifier where present.
2. Results have deterministic order: input alignment order, then rule catalog order.
3. Every finding identifies `rule_id`, `rule_version`, `ruleset_version`, `outcome`, related IDs, severity, reviewer requirement, and machine-readable reason.
4. Spec 005 provides a severity hint only. Spec 007 owns the final severity policy and approval effect.
5. The engine makes no network or LLM call.

## Functional requirements

- **FR-11:** Detect numerical and unit mismatches through exact, documented normalization; valid equivalents must not produce findings.
- **FR-16:** Execute deterministic, versioned validations for contracts, numeric values, units, and source evidence references without probabilistic inference.
- **DVE-001:** Each submitted source fact and claim in a validation run MUST appear in exactly one immutable alignment record. A numeric comparison is evaluated only when that record has `status=ALIGNED`, references exactly one source fact and claim, and declares a shared measurement category. `UNAVAILABLE`, `AMBIGUOUS`, or `REJECTED` alignment records emit one `ALIGN-001` `NOT_EVALUABLE` result with the matching stable reason and do not emit `NUM-001` through `NUM-005`. A run missing a required alignment record is rejected as `SCHEMA_ERROR`/provenance-invalid; it must not return an empty successful comparison.
- **DVE-002:** Canonical numeric parsing accepts only documented decimal representations (German comma or dot decimal separator; optional sign; no locale guessing). Parsing failure yields `STR-001`.
- **DVE-003:** The Ruleset `DVE-RULESET-v1` permits only `TEMPERATURE`, `FLUID_INTAKE`, `MEDICATION_QUANTITY`, and `BLOOD_PRESSURE`. The reference-only public request cannot submit a category; when a referenced immutable source fact or claim resolves to an unknown category, the resolver rejects the run as `SCHEMA_ERROR`/provenance-invalid. No unsupported category is silently compared.
- **DVE-004:** Unit conversion is exact decimal arithmetic. v1 allows Celsius↔Celsius, millilitre↔litre for fluid volume, and milligram↔gram for medication mass. Category/unit pairing is defined in `data-model.md`; no implicit conversion is allowed.
- **DVE-005:** Equal values after a permitted conversion yield no `NUM-001`; the engine may expose an informational `NUM-002` pass record only when an API consumer requests rule trace output. Default reviewer findings omit passes.
- **DVE-006:** Incompatible dimensions yield `NUM-003`; unknown/invalid category-unit pairs yield `STR-003`, not a numeric mismatch.
- **DVE-007:** Blood pressure must be a typed two-component value with unit `mmHg`; parse and compare systolic and diastolic values separately. Any changed component yields one `NUM-005` finding naming changed components.
- **DVE-008:** Approximation comparison uses only `EXACT`, `APPROXIMATE`, or `UNSPECIFIED` structured values. `APPROXIMATE → EXACT` yields `NUM-004`; any `UNSPECIFIED` state is `NOT_EVALUABLE` for this rule.
- **DVE-009:** Evidence integrity is evaluated for each supplied evidence reference independent of numeric comparability. `EVD-001`–`EVD-003` are failures and take precedence over a positive numeric pass for that reference.
- **DVE-010:** Schema-invalid request envelopes are rejected with `SCHEMA_ERROR`; field-valid items with a rule precondition failure yield individually traceable `NOT_EVALUABLE` findings.
- **DVE-011:** A failed finding includes `expected_value` and `observed_value` where meaningful, exact source/claim/alignment/evidence-reference IDs, a stable reason, and `requires_review=true`. Missing values are explicit `null`, never invented. `evidence_reference_ids` is required and may be an empty array only when no evidence reference is relevant to that rule.
- **DVE-012:** The engine preserves all outcomes; it does not collapse a deterministic failure into a semantic status from Spec 004 or overwrite a Spec 004 finding.

## Rule catalog

| Rule ID | Trigger and outcome |
| --- | --- |
| `ALIGN-001` | Alignment status is `UNAVAILABLE`, `AMBIGUOUS`, or `REJECTED`: `NOT_EVALUABLE/ALIGNMENT_<STATUS>`. |
| `NUM-001` | Comparable scalar canonical values differ: `FAIL/NUMERIC_MISMATCH`. |
| `NUM-002` | Permitted exact conversion is applied; equivalent values pass. Optional trace only. |
| `NUM-003` | Units have incompatible dimensions: `FAIL/INCOMPATIBLE_UNIT`. |
| `NUM-004` | Explicit structured approximation becomes exact: `FAIL/PRECISION_MISMATCH`. |
| `NUM-005` | Comparable blood-pressure component differs: `FAIL/COMPOSITE_MEASUREMENT_MISMATCH`. |
| `STR-001` | Numeric measurement representation cannot parse: `FAIL/INVALID_STRUCTURED_FIELD_TYPE`. |
| `STR-002` | Claim lacks required note revision: `FAIL/MISSING_REQUIRED_REFERENCE`. |
| `STR-003` | Category/unit pair is invalid: `FAIL/INVALID_UNIT_CATEGORY_PAIRING`. |
| `EVD-001` | Evidence offset is invalid for immutable transcript text: `FAIL/INVALID_SOURCE_SPAN`. |
| `EVD-002` | Evidence source/version differs from run source identity: `FAIL/SOURCE_VERSION_MISMATCH`. |
| `EVD-003` | Quotation differs from the authoritative source substring: `FAIL/EVIDENCE_TEXT_MISMATCH`. |

## Data contracts

The public request is provenance by reference: it contains exact source identity plus source-fact, claim, and alignment identifiers; the service resolves immutable records before calling the engine. The engine's internal input is the resolved normalized source facts, claims, alignment records, and immutable transcript snapshot. The normative transport schema is [contracts/deterministic-validation.openapi.yaml](contracts/deterministic-validation.openapi.yaml). The domain definition and unit table are [data-model.md](data-model.md). All contract versions start at `v1` and are immutable after publication.

`ValidationFinding` has this minimum shape:

```json
{
  "rule_id": "NUM-001",
  "rule_version": "1",
  "ruleset_version": "DVE-RULESET-v1",
  "outcome": "FAIL",
  "source_fact_id": "fact-001",
  "claim_id": "claim-001",
  "evidence_reference_ids": ["evidence-fact-001"],
  "severity": "CRITICAL",
  "expected_value": "37.2",
  "observed_value": "38.2",
  "unit": "celsius",
  "message": "Temperature differs from source",
  "requires_review": true
}
```

`severity` is a v1 transport hint (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) attached by the calling policy/configuration. Spec 005's default mapping is documented in the plan solely to make fixtures stable; Spec 007 is the authority for final severity and blocking behavior.

## Acceptance scenarios

| Test ID | Scenario | Expected result |
| --- | --- | --- |
| AT-001 | Source `37,2 C`; claim `37.2 C` | No failure; equal canonical values. |
| AT-002 | Source `37,2 C`; claim `38,2 C` | `FAIL`, `NUM-001`. |
| AT-003 | Source `0,5 L`; claim `500 ml` | No failure; valid `NUM-002` conversion. |
| AT-004 | Source `500 ml`; claim `500 mg` | `FAIL`, `NUM-003`. |
| AT-005 | Source `120/80 mmHg`; claim `140/80 mmHg` | `FAIL`, `NUM-005`; systolic named. |
| AT-006 | Structured source `APPROXIMATE 200 ml`; claim `EXACT 200 ml` | `FAIL`, `NUM-004`. |
| AT-007 | Request has no claim ID | Reject `SCHEMA_ERROR`. |
| AT-008 | Evidence end offset exceeds transcript length | `FAIL`, `EVD-001`. |
| AT-009 | Evidence uses an outdated source version | `FAIL`, `EVD-002`. |
| AT-010 | Evidence quotation differs from source substring | `FAIL`, `EVD-003`. |
| AT-011 | Source fact and claim have no reliable alignment | `NOT_EVALUABLE`, `ALIGN-001`; no numeric contradiction invented. |
| AT-012 | Identical valid input executed repeatedly | Identical normalized result ordering and content. |
| AT-013 | Aligned scalar source or claim has non-parseable value text | `FAIL`, `STR-001`; dependent NUM rules skipped. |
| AT-014 | Resolved claim lacks its note revision | `FAIL`, `STR-002`; comparison not treated as successful. |
| AT-015 | Fluid-intake record uses `CELSIUS` | `FAIL`, `STR-003`; no unit conversion or numeric mismatch. |
| AT-016 | Referenced immutable source fact or claim resolves to an unsupported measurement category | Reject `SCHEMA_ERROR`/provenance-invalid. |

## Non-functional requirements and definition of done

- Pure rule execution is deterministic, offline, reproducible, and independently testable with `pytest`.
- The engine uses synthetic fixtures only and does not log full transcript or claim text outside approved evidence excerpts.
- Every output is traceable to immutable source identity, source fact ID, claim ID, alignment ID where applicable, rule ID/version, and ruleset version.
- Unit, contract, property/boundary, integration, and acceptance tests pass, including all AT cases.
- The versioned response contract is sufficient for Spec 007 rendering and the rule/fixture manifest is sufficient for Spec 008 evaluation.
- The reviewer-owned [checklist.md](checklist.md) must be approved before implementation.
