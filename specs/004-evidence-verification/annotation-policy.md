# Spec 004 — Evidence Annotation Policy

**Policy version:** `EVIDENCE_ANNOTATION-v1`  
**Applies to:** successful semantic-verification findings under [spec.md](spec.md)  
**Purpose:** Provide canonical labels for fixture annotation and development acceptance. It does not turn model interpretation into deterministic text reasoning.

## Decision ownership

The semantic verifier determines the proposed relationship between a claim and the immutable source: support, explicit contradiction, unresolved ambiguity, or insufficient support. Deterministic code validates only the response contract, claim coverage, enum values, required labels, source identity, character ranges, source-derived quotations, and run-state rules.

Deterministic code MUST reject invalid output, but MUST NOT infer that text semantically supports or contradicts a claim. Where deterministic integrity checks and a verifier recommendation differ, retain both records and resolve blocking integrity failures conservatively.

## Canonical labels

| ID | Source and claim condition | Primary status | Required discrepancy | Span rule |
|---|---|---|---|---|
| AP-001 | Source directly establishes the complete claim and material qualifiers. | `SUPPORTED` | None unless another material qualifier changed. | At least one valid supporting span. |
| AP-002 | Source explicitly states the opposite proposition, including explicit negation reversal. | `CONTRADICTED` | `NEGATION` when polarity/negation differs. | At least one valid conflicting span. |
| AP-003 | No relevant source evidence supports the claim and no source evidence explicitly conflicts. | `UNSUPPORTED` | `CLINICAL_INFERENCE` when an unestablished diagnosis is asserted. | No span is required. An optional valid context span is allowed only when its paired quotation is marked `CONTEXT_NON_SUPPORTING`; it cannot be presented as support or conflict. |
| AP-004 | Relevant source evidence is qualified or ambiguous, so the asserted claim cannot be established or explicitly contradicted. | `UNCERTAIN` | The applicable qualifier label below. | At least one valid relevant span. |
| AP-005 | Source says a symptom is possible/unclear; claim asserts it as certain. | `UNCERTAIN` | `CERTAINTY` | At least one valid relevant span. |
| AP-006 | Source explicitly says confirmation cannot be made or was withheld; claim asserts confirmation. | `CONTRADICTED` | `CERTAINTY`; add `CLINICAL_INFERENCE` for an unsupported diagnosis. | At least one valid conflicting span. |
| AP-007 | Source is a patient or third-party report; claim asserts a confirmed clinical observation. | `UNCERTAIN` | `ATTRIBUTION` | At least one valid report span. |
| AP-008 | Source says “Keine starken Schmerzen”; claim says “Keine Schmerzen,” with no other resolving evidence. | `UNCERTAIN` | `NEGATION` | At least one valid partial-negation span. |

## Run-outcome distinction

`UNSUPPORTED` is a successful evidence finding when the claim has been semantically assessed and the response is contract-valid. It may have no span, or optional valid context spans whose paired quotations are explicitly marked `CONTEXT_NON_SUPPORTING`; it is never a verifier failure.

An invalid, mismatched, empty, out-of-range, or unresolvable required source span is an evidence-integrity failure. The verification run is non-successful and must contain no authoritative partial findings. This distinction is mandatory in the OpenAPI contract and test fixtures.

## Fixture and evaluation use

EV-005 maps to AP-005 unless the source explicitly denies or withholds confirmation, in which case AP-006 applies. EV-006 maps to AP-007. EV-013 maps to AP-008. Fixtures MUST store the policy version, expected primary status, required discrepancy labels, and expected span rule.

The fixed development dataset may be used by a configured real verifier to report deviations from these labels. The held-out benchmark, release thresholds, and quality claims remain owned by Spec 008.
