# Spec 006 - Source Coverage & Completeness Verification

**Canonical feature specification:** This `spec.md` is the authoritative behavioural specification for Spec 006.  
**Feature:** Source-to-note coverage verification for German nursing documentation  
**Status:** Ready for reviewer requirements-quality review  
**Primary requirement:** FR-14 - Detect important omissions  
**Dependencies:** immutable transcript and spans (Spec 001), immutable note revisions (Spec 002), note claims (Spec 003), claim evidence findings (Spec 004), deterministic numeric findings (Spec 005), review/severity policy (Spec 007), and benchmark evaluation (Spec 008).

## Purpose

Ensure important information explicitly stated in a caregiver's German transcript is not accidentally omitted from the generated nursing note. This is the source-to-note half of the reliability engine. It complements, and does not replace, Spec 004's note-to-source evidence verification.

A result in which each remaining note claim is supported is not sufficient to establish documentation completeness. This feature identifies expected source facts that are absent, incomplete, semantically changed, or not reliably assessable so a human can review the exact transcript evidence before any approval decision.

Coverage statuses are source-to-note statuses and are distinct from Spec 004's note-claim evidence statuses (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN`). A run must preserve both result families without silently translating one into the other.

## Scope and non-goals

### In scope

- Extract atomic, source-linked facts explicitly present in the immutable German transcript.
- Consider symptoms, negated symptoms, numerical measurements, mobility observations, care actions, and stated uncertainty; other explicitly documented nursing facts may be extracted when they meet the expected-fact policy.
- Preserve fact text, subject when explicit, polarity, certainty, attribution, temporal qualifier, numeric value/unit/approximation, laterality, and other material attributes.
- Match expected source facts to the exact note revision's immutable Spec 003 claims using semantic comparison.
- Classify each expected fact as `COVERED`, `PARTIALLY_COVERED`, `MISSING`, `DISTORTED`, or `UNCERTAIN`.
- Return structured, source-grounded coverage findings and association links to relevant Spec 004/005 findings.
- Create a new immutable run for every note revision re-evaluation.
- Report runtime coverage counts and support Spec 008's separately annotated benchmark metrics.

### Out of scope

- Generating diagnoses, deciding clinical truth, giving treatment advice, or determining clinical urgency.
- Editing, inserting text into, approving, or resolving the candidate note.
- Replacing Spec 004's support/contradiction assessment or Spec 005's numeric/unit rules.
- Assigning final severity, review disposition, or approval effects. Spec 007 owns the versioned severity and approval policy.
- Requiring verbatim repetition of non-material source wording.

## Definitions

| Term | Meaning |
| --- | --- |
| Source snapshot | Exact immutable transcript identified by `sourceId` and `sourceVersion`. |
| Source fact | One independently assessable, explicitly stated proposition extracted from the source snapshot and anchored to one or more valid source spans. |
| Expected source fact | A source fact whose `documentationExpectation` is `REQUIRED` or `IMPORTANT` under `COVERAGE_EXPECTATION-v1`; it belongs in the runtime coverage denominator. |
| Contextual fact | An extracted fact labeled `CONTEXTUAL`; it is retained for traceability but excluded from the completeness denominator and does not generate an omission finding by itself. |
| Candidate claim | An immutable atomic claim from the exact Spec 003 extraction run for the candidate note revision. |
| Coverage run | Immutable result for one source snapshot, note revision, source-fact extraction run, and candidate-claim extraction run. |
| Material attribute | An attribute that changes the documented meaning: polarity, certainty, attribution, subject, temporal qualifier, laterality, numeric value/unit/approximation, care action, mobility assistance, or other policy-marked attribute. |
| Coverage finding | A reviewer-facing record for an expected fact that is not faithfully covered, including its source evidence and safe suggested review text. |

Offsets are Unicode code-point positions in the exact immutable transcript string: zero-based, start-inclusive, and end-exclusive. Whitespace, punctuation, line endings, and non-BMP characters participate in offsets. A display-normalized transcript must never be used to compute evidence ranges.

## Coverage status policy

The coverage status definitions and precedence are versioned as `COVERAGE_STATUS-v1`.

| Status | Meaning | Required handling |
| --- | --- | --- |
| `COVERED` | A note claim faithfully represents the source fact and all material attributes. | No omission finding is generated. |
| `PARTIALLY_COVERED` | A related note claim represents the fact but omits one or more material attributes without changing the represented attribute. | Generate a review finding naming the missing attributes. |
| `MISSING` | No candidate claim semantically represents the expected source fact. | Generate an omission finding. |
| `DISTORTED` | A related note claim represents the fact but changes one or more material attributes or its factual meaning. | Generate a review finding and link an overlapping contradiction finding when available. |
| `UNCERTAIN` | A reliable coverage decision cannot be made. This includes a structured, source-linked extraction uncertainty or semantically unresolved match; it is never a successful coverage assertion. | Generate an `UNCERTAIN` review finding, but never invent a fact or claim. |

The comparison outcome is selected in this order for each expected source fact:

1. `UNCERTAIN` when the fact was not reliably extracted or semantic comparison is unresolved.
2. `DISTORTED` when a related note claim changes a material attribute, including incompatible numeric values, reversed polarity, lost uncertainty rendered as definite, changed laterality, or changed temporal meaning.
3. `COVERED` when at least one claim faithfully preserves every material attribute.
4. `PARTIALLY_COVERED` when a related claim retains the fact but omits a material attribute and no faithful claim exists.
5. `MISSING` when no related claim represents the fact.

`DISTORTED` takes precedence over `PARTIALLY_COVERED` only when no other candidate claim faithfully covers the fact. A distinct faithful claim therefore prevents a fact from being reported as omitted merely because another sentence restates it incorrectly; the linked contradiction remains available to Spec 004/005 and Spec 007.

## Expected-fact policy and severity handoff

`COVERAGE_EXPECTATION-v1` is a fixed PoC policy, not an LLM severity decision.

| Source fact category | Default documentation expectation | Spec 007 policy key |
| --- | --- | --- |
| Explicit temperature or other vital numerical measurement | `REQUIRED` | `MEASUREMENT_OMISSION` |
| Explicitly reported or observed pain/symptom, including explicit absence | `IMPORTANT` | `SYMPTOM_OMISSION` |
| Mobility observation requiring assistance or describing limitation | `IMPORTANT` | `MOBILITY_ASSISTANCE_OMISSION` |
| Performed care action | `IMPORTANT` | `CARE_ACTION_OMISSION` |
| Explicit uncertainty modifying an expected fact | Same expectation as its fact | `UNCERTAINTY_OMISSION` |
| Nonessential stylistic wording or redundant detail | `CONTEXTUAL` | none |

The feature returns `documentationExpectation` and `severityPolicyKey`, not a final severity. Spec 007 maps those inputs to the current `minor`, `major`, or `critical` engineering labels, records its policy version, and determines any review/approval consequence. Neither the coverage engine nor a model may freely invent severity.

## User stories and acceptance criteria

### US-1 - Extract expected source facts (P1)

As a caregiver reviewer, I need atomic, evidence-linked source facts so I can inspect exactly what the system expects the note to cover.

**Acceptance criteria**

1. Every extracted source fact has one or more non-empty, valid source spans in the requested immutable transcript version.
2. Compound source statements are split when their components can differ in coverage, such as a symptom and a care action in the same sentence.
3. Fact attributes retain explicit negation, certainty, attribution, time, numeric value/unit/approximation, laterality, and assistance information.
4. The extractor does not create a source fact without reliable source evidence. It records a source-linked `UNCERTAIN` extraction item instead.
5. Facts are labeled `REQUIRED`, `IMPORTANT`, or `CONTEXTUAL` by the documented policy, not a model-created severity.

### US-2 - Match facts semantically (P1)

As a caregiver reviewer, I need faithful German paraphrases to count as covered so harmless wording changes do not create false omission alerts.

**Acceptance criteria**

1. Semantic equivalence may count as coverage when subject, polarity, certainty, attribution, temporal meaning, and all other material attributes remain faithful.
2. Exact string equality alone is insufficient.
3. `Frau Müller klagte über Schmerzen im linken Knie.` is covered by `Bewohnerin berichtet über linksseitige Knieschmerzen.` when identifiers and material attributes resolve consistently.
4. `Linkes Knie` rewritten only as `Knieschmerzen` is `PARTIALLY_COVERED` because laterality is material.
5. A source statement qualified as uncertain and rewritten as definite is `DISTORTED`.

### US-3 - Classify and expose omissions (P1)

As a caregiver reviewer, I need one transparent coverage status for every expected source fact so I can prioritize what needs review.

**Acceptance criteria**

1. Every expected source fact in a successful run has exactly one coverage assessment.
2. `COVERED` means faithful representation; `PARTIALLY_COVERED`, `MISSING`, `DISTORTED`, and `UNCERTAIN` never count as faithfully covered.
3. A `MISSING` or `PARTIALLY_COVERED` expected fact produces a structured source-grounded omission finding.
4. A `DISTORTED` finding contains the incompatible claim reference and links to a corresponding Spec 004 contradiction and/or Spec 005 mismatch where one exists.
5. `UNCERTAIN` does not claim that an undocumented fact exists and must explain the decision limit.

### US-4 - Preserve revision and human-review boundaries (P1)

As an operator, I need coverage checks tied to exact immutable versions so a note edit is never mistaken for a resolved omission.

**Acceptance criteria**

1. A run binds source ID/version, note ID/revision, source-fact extraction run, and claim-set extraction run.
2. An amended note uses a new note revision and a new coverage run; old runs and findings remain immutable.
3. The service cannot alter source text, note text, claims, or a reviewer decision.
4. Invalid provenance, malformed semantic output, invalid spans, unavailable dependencies, or missing claim coverage produce a non-successful run, not a passing result.
5. The response contains no approval state and no assertion that a care observation is medically true.

### US-5 - Measure completeness honestly (P2)

As an evaluator, I need completeness and omission-detection metrics that cannot be inflated by silently failing to extract source facts.

**Acceptance criteria**

1. Runtime counts explicitly state that they are derived from the run's extracted expected facts and are not benchmark ground truth.
2. The held-out completeness metric uses manually annotated expected facts from the Spec 008 synthetic benchmark:

   `completeness = faithfully covered annotated expected facts / applicable annotated expected facts`

3. `PARTIALLY_COVERED`, `MISSING`, `DISTORTED`, and `UNCERTAIN` are not faithfully covered in the numerator.
4. The benchmark also reports omission detection recall and false omission warning rate with counts and denominators.
5. The held-out split is not used for prompt/rule tuning.
6. The Spec 008 handoff also supports constitution-wide reporting of critical-error recall, false-positive rate, claim classification performance, latency, inference cost, and reviewer workload with stated denominators.

## Functional requirements

- **FR-14.1:** Extract atomic source facts with valid immutable-transcript evidence spans.
- **FR-14.2:** Represent source-fact expectation, negation, certainty, attribution, temporal qualifiers, and applicable material attributes.
- **FR-14.3:** Semantically compare every expected source fact with candidate claims from the requested note revision.
- **FR-14.4:** Assign exactly one `COVERED`, `PARTIALLY_COVERED`, `MISSING`, `DISTORTED`, or `UNCERTAIN` status to every expected source fact in a successful run.
- **FR-14.5:** Generate structured, source-grounded review findings for all non-covered expected facts; findings must not silently modify the note.
- **FR-14.6:** Preserve and expose correlation links to overlapping Spec 004 contradiction and Spec 005 numeric/unit findings.
- **FR-14.7:** Re-evaluate coverage for each new immutable note revision without mutating historical runs.
- **FR-14.8:** Calculate held-out completeness only from manually annotated benchmark facts and report omission recall and false-warning rate.
- The source transcript is the sole authority for expected-fact evidence. Candidate note prose, claims, model memory, retrieval scores, and prior findings cannot create source facts.
- A semantic verifier is untrusted structured input. Deterministic validation must verify source spans, immutable identities, result closure, and permitted status/attribute values before a run succeeds.
- Every run records the source text hash and declared normalization policy, resident context reference, ruleset, dataset, model, prompt, and provider versions, correlation ID, and idempotency key.
- The implementation uses synthetic data only and keeps content out of logs except minimal source-derived excerpts needed for review.

## Data contracts

The normative detailed shapes are in [data-model.md](data-model.md) and [contracts/coverage-runs.openapi.yaml](contracts/coverage-runs.openapi.yaml). The public request is reference-only: callers may not submit transcript prose, source-fact values, candidate claim prose, or a desired status.

### SourceFact

An immutable extracted fact has `sourceFactId`, source ID/version, resident context reference, source text hash, normalization policy, source-fact extraction run ID, category, normalized assertion/attributes, expectation, optional Spec 007 policy key, and one or more source spans. A fact must be atomic enough to independently receive a coverage status.

### UnresolvedSourceItem

An extractor may return a source-linked unresolved item only when it cannot reliably identify a fact. It has an ID, non-empty candidate source span(s), explanation, and no asserted fact value. It produces an `UNCERTAIN` coverage assessment and is excluded from completeness denominator because the fact itself is not established.

### CoverageAssessment

One assessment exists for every expected source fact and unresolved source item. It contains its status, matched claim IDs, material attributes preserved/missing/distorted, explanation, source evidence, and related external finding references. Exactly one `COVERED` assessment is not a review finding; all other statuses create a `CoverageFinding` requiring human review.

### CoverageFinding

A finding contains a stable ID, status, expected-fact or unresolved-item reference, source spans and source-derived quotes, candidate claim references where applicable, missing/distorted attributes, expectation, Spec 007 policy key, suggestion text derived only from source evidence, related findings, `requiresReview: true`, and policy versions. Suggestion text is review aid only and must never be inserted automatically.

### CoverageRun

A successful run contains one assessment for every and only every resolved expected source fact and unresolved source item, plus complete version/provenance metadata (including resident context, source hash/normalization, ruleset, dataset, provider/model/prompt, correlation, and idempotency data), execution metrics, and runtime counts. A non-successful run contains a typed failure, never authoritative partial assessments.

## API

`POST /api/v1/coverage-runs` creates one bounded synchronous terminal coverage run for an exact source snapshot and candidate note revision. The request identifies the source, note revision, source-fact extraction run, and candidate claim-set extraction run by ID. The service resolves immutable records; it never trusts request-supplied prose or fact values.

HTTP 200 returns a terminal immutable run: either a successful run with coverage assessments or a structured non-successful run. Syntax errors use the contract's schema-error envelope. Missing or conflicting immutable references return stable non-success errors. This PoC has no mutation endpoint, no asynchronous/polling contract, and no auto-fix endpoint.

## Acceptance scenarios

| Test ID | Source and note behaviour | Expected result |
| --- | --- | --- |
| COV-001 | All expected source facts are faithfully represented. | All expected facts are `COVERED`; no findings; runtime numerator equals denominator. |
| COV-002 | Explicit temperature measurement is absent from the note. | Temperature fact is `MISSING`; source-grounded finding has `MEASUREMENT_OMISSION`. |
| COV-003 | `Schmerzen im linken Knie` becomes `Knieschmerzen`. | `PARTIALLY_COVERED`; `laterality` is listed as missing. |
| COV-004 | German clinical/colloquial paraphrase preserves material attributes. | `COVERED`; exact string equality is not required. |
| COV-005 | An explicit negative symptom statement is omitted. | `MISSING`; polarity is retained in the source fact and finding. |
| COV-006 | A source uncertainty is rewritten as a definite assertion. | `DISTORTED`; `certainty` is listed as distorted and relevant Spec 004 finding is linked when supplied. |
| COV-007 | Important source fact is absent from an otherwise evidence-valid note. | Omission finding is generated; the feature does not approve or change the note. |
| COV-008 | A revised note includes a previously missing fact. | New revision receives a new run and fact is re-evaluated; historical run is unchanged. |
| COV-009 | The source extractor cannot reliably establish a fact from a source passage. | `UNCERTAIN` unresolved-item assessment, source-linked explanation, no invented `SourceFact`, excluded from denominator. |
| COV-010 | Source and related note claim use incompatible numerical values. | `DISTORTED`; linked to the relevant Spec 005 finding and Spec 004 contradiction when available. |

Fixtures must additionally cover multi-clause German statements, temporal modifiers, approximate measurements, indirect speech, Unicode offsets, and negations. Tests assert exact source/item IDs, status, attributes, source locations, claim links, related-finding links, and denominator treatment rather than merely a warning string.

## Non-functional requirements and definition of done

- Source fact extraction, semantic matching, contracts, run persistence, and all results are traceable to immutable source/note versions and policy/provider/prompt versions.
- Span integrity is deterministic and source-derived quotations must equal the exact transcript substring.
- A successful run has complete, unique expected-fact and unresolved-item coverage; semantic provider failure never creates partial authoritative results.
- Equivalent German wording must be accepted only when material attributes remain faithful.
- Review findings are actionable, minimized, source-grounded, and require human review; no component approves or edits a note.
- Acceptance, contract, unit, integration, revision, benchmark-handoff, and failure-path tests pass using synthetic data.
- Held-out evaluation results include raw counts, denominator, completeness, omission-detection recall, and false omission warning rate. Spec 008 owns thresholds and release decisions.

