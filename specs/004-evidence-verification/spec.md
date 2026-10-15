# Spec 004 — Evidence Verification

**Canonical feature specification:** This `spec.md` file is the authoritative behavioral specification for Spec 004.

**Feature:** Evidence-grounded verification of nursing-note claims  
**Status:** Requirements reviewed; implementation integration pending
**Input dependencies:** immutable German transcript (Spec 001), candidate note revision (Spec 002), and atomic claims (Spec 003)  
**Primary requirements:** FR-07, FR-08, FR-09, FR-10, FR-12, FR-13

## Purpose

Build the reliability component that decides whether every atomic factual claim in a generated or externally supplied nursing note is grounded in the original German transcript. The service produces evidence-linked findings that deterministic validation, a caregiver reviewer, and later evaluation components can independently inspect.

The source transcript is the only evidence source. A candidate note, surrounding note prose, prior verification output, or model memory must never support that note's own claims.

Claims are supplied by immutable reference, not re-submitted by value: each request supplies a claim ID and the synthetic resident ID, then the service resolves the immutable Spec 003 claim record. `claimSetId` is the exact upstream immutable `extractionRunId`; it binds every requested claim to one extraction result. The resolved record must belong to that claim set and exact note revision. Unknown, stale, cross-note, altered, or resident-mismatched claim references are non-successful validation outcomes. The PoC never infers or disambiguates a resident; the supplied synthetic resident ID must match the source record.

## Scope

### In scope

- Verify every extracted claim for one immutable transcript version and one candidate note revision.
- Assign exactly one primary evidence status: <code>SUPPORTED</code>, <code>UNSUPPORTED</code>, <code>CONTRADICTED</code>, or <code>UNCERTAIN</code>.
- Link grounded findings to validated source character spans and source-derived quotations.
- Detect and explain material changes in negation, certainty, attribution, and unsupported clinical inference.
- Fail safely on stale, malformed, missing, or inconsistent provenance, evidence, and verifier results.
- Persist traceable verification runs and expose them through the verification-runs API.

### Out of scope

| Capability | Owner |
|---|---|
| Transcript ingestion, storage, normalization, and versioning | Spec 001 |
| Nursing-note generation | Spec 002 |
| Atomic claim extraction | Spec 003 |
| Numerical and unit validation | Spec 005 |
| Source-to-note completeness and important omissions | Spec 006 |
| Caregiver edits, approval, severity, and audit decisions | Spec 007 |
| Held-out benchmark metrics, release thresholds, and regression reporting | Spec 008 |

Spec 004 may consume normalized claim attributes from upstream components. It must not alter transcripts, claims, or nursing notes. Spec 004 owns only the development-acceptance report required before configured-verifier use; held-out benchmark metrics and release thresholds remain owned by Spec 008.

## Definitions

| Term | Meaning |
|---|---|
| Source transcript | Immutable original German transcript identified by source ID and source version. |
| Candidate note revision | Exact note revision whose extracted claims are checked, identified by note ID and note revision. |
| Claim | Atomic, externally checkable proposition from Spec 003 belonging to the candidate note revision. |
| Evidence span | Non-empty source character range, represented by a zero-based, start-inclusive and end-exclusive offset. |
| Evidence quotation | Source substring recovered from an evidence span; derived data, never independently trusted. |
| Verification run | Immutable result for one source version, note revision, and claim set. |

## Evidence-status policy

| Status | Meaning | Example |
|---|---|---|
| <code>SUPPORTED</code> | Evidence faithfully establishes the complete claim and its material qualifiers. | “Keine Schmerzen” → “Verneint Schmerzen.” |
| <code>UNSUPPORTED</code> | Source lacks sufficient support; it does not explicitly say the opposite. | “Patient ist dehydriert,” when dehydration is never mentioned. |
| <code>CONTRADICTED</code> | Source explicitly conflicts with the claim. | “Keine Schmerzen” → “Hat Schmerzen.” |
| <code>UNCERTAIN</code> | Relevant evidence exists but is ambiguous or qualified such that no definitive result is justified. | “Vielleicht Schmerzen” → “Hat Schmerzen.” |

When signals overlap, classify in this order:

1. An explicit valid semantic conflict is <code>CONTRADICTED</code>.
2. Otherwise, faithful evidence is <code>SUPPORTED</code>.
3. Otherwise, relevant unresolved evidence is <code>UNCERTAIN</code>.
4. Otherwise, use <code>UNSUPPORTED</code>.

An execution, schema, provenance, or evidence-integrity failure is not an evidence status. It makes the run non-successful and leaves the candidate note unapproved.

### Qualifier policy

- **Negation:** Losing, adding, or reversing explicit negation is a contradiction when it reverses the asserted proposition. Scope must be preserved: “keine starken Schmerzen” does not faithfully establish “keine Schmerzen.”
- **Certainty:** Turning qualified evidence into a definitive assertion must be flagged. It is <code>CONTRADICTED</code> only if the versioned annotation policy says the source qualification conflicts with the assertion; otherwise it is <code>UNCERTAIN</code>.
- **Attribution:** Patient report, carer report, and confirmed clinical observation are distinct assertions. A report rewritten as confirmed observation is not directly supported by the report alone.
- **Clinical inference:** A diagnosis requires source support for that diagnosis, not merely observations from which a clinician might infer it. An unestablished conclusion is <code>UNSUPPORTED</code>.
- **Terminology:** Equivalent German medical and colloquial wording may be supported only when meaning, polarity, certainty, attribution, temporality, and subject remain faithful.

## User stories and acceptance criteria

### US-1 — Verify a claim against original evidence (P1)

As a caregiver or downstream validator, I need every extracted claim checked against the immutable German transcript so I can distinguish grounded documentation from unsupported content.

**Acceptance criteria**

1. A valid run processes every supplied claim that belongs to the requested candidate note revision.
2. Every processed claim in a successful run has one and only one primary evidence status.
3. A supported finding has at least one valid source span that grounds the whole claim.
4. An explicit conflict yields <code>CONTRADICTED</code> and identifies conflicting evidence.
5. Missing sufficient support without explicit conflict yields <code>UNSUPPORTED</code>.
6. Relevant but unresolved ambiguity yields <code>UNCERTAIN</code> and an explanation.

### US-2 — Inspect evidence grounding (P1)

As a caregiver reviewer, I need every finding tied to exact transcript characters so I can independently check the result.

**Acceptance criteria**

1. Every span identifies the source ID and immutable source version used by the run.
2. Span boundaries are valid under the documented offset convention.
3. Returned quotation equals the source substring at those boundaries; a verifier-provided quotation is never trusted.
4. A span failure makes the run non-successful rather than returning a finding with untrusted grounding.

### US-3 — Preserve clinical meaning (P1)

As a safety reviewer, I need semantic meaning changes detected, especially negation, certainty, attribution, and unsupported diagnoses.

**Acceptance criteria**

1. Explicit negation reversal is <code>CONTRADICTED</code> and identifies negation.
2. Certainty increase is flagged, uses the versioned policy, and records that policy version.
3. Changing a patient report to a confirmed observation is flagged as attribution change and is not direct support.
4. An observation rewritten as an unestablished diagnosis is <code>UNSUPPORTED</code>.
5. Partial negation is evaluated at its true scope, not merely by presence of a negative token.

### US-4 — Fail safely and remain traceable (P1)

As an operator, I need bad provenance, evidence, or verifier output to be unmistakable failures so no unverified note appears approved.

**Acceptance criteria**

1. Reject missing transcripts, source-version mismatch, missing claims, and claims belonging to another note revision.
2. Timeout, malformed structured output, unknown status, duplicate result, or missing result for a valid claim produces a non-successful run.
3. A successful run records source ID/version, note ID/revision, claim-set identity, model/version, prompt version, annotation-policy version, timestamps, and execution status.
4. Failure information is separate from evidence status and must not present findings as authoritative.
5. A compound claim MUST NOT receive <code>SUPPORTED</code> when any material assertion in it lacks source evidence. Atomic assertions are evaluated independently; if a compound claim contains both supported and unestablished assertions, its aggregate status is <code>UNCERTAIN</code> or <code>UNSUPPORTED</code>.

## Functional requirements

- **FR-07:** Verify every extracted claim against the requested source transcript version.
- **FR-08:** Link grounded findings to valid source character spans and source-derived quotations.
- **FR-09:** Use <code>UNSUPPORTED</code> where source evidence is insufficient and not explicitly conflicting.
- **FR-10:** Use <code>CONTRADICTED</code> where source information explicitly conflicts.
- **FR-12:** Evaluate and expose material negation, certainty, and attribution changes.
- **FR-13:** Use <code>UNSUPPORTED</code> for clinical conclusions the transcript does not establish.
- **FR-14:** Evaluate material assertions within a compound claim independently and never classify the entire claim as <code>SUPPORTED</code> from partial semantic overlap.
- Use only the requested source transcript as evidence.
- Preserve one-and-only-one primary classification per claim in every successful run.
- Never silently repair source text, claim text, note text, source versions, or evidence offsets.
- Preserve model and execution failures separately from evidence classifications.
- Return stable, schema-valid API responses.

## Data contracts

### EvidenceStatus

Enumeration with exactly: <code>SUPPORTED</code>, <code>UNSUPPORTED</code>, <code>CONTRADICTED</code>, <code>UNCERTAIN</code>.

The definitions and precedence in this specification are versioned as `EVIDENCE_STATUS-v1`. A change to a status definition or precedence requires a new policy version and regression cases.

Canonical ground-truth classification for qualifier-sensitive fixtures is defined in [annotation-policy.md](annotation-policy.md) as `EVIDENCE_ANNOTATION-v1`. The semantic verifier applies that policy; deterministic code validates the resulting contract and evidence integrity without independently deciding semantic support or contradiction.

Certainty is a label within `EVIDENCE_ANNOTATION-v1` and uses that canonical policy version.

### ClaimInput

`ClaimInput` is a provenance reference, not a claim payload. It contains only
`claimId` and `residentTestId`; assertion text and normalized attributes are
rejected as unknown request fields so they cannot be altered in transit. The
service resolves `claimId` from the immutable claim repository and validates
that its claim-set ID, note ID/revision, and synthetic resident exactly match
the request and source record. `UNKNOWN` is not a valid resident input.

### SourceSpan

The canonical domain shape follows `docs/architecture.md`: `source_id`, `source_version`, `start`, and `end`. Transport serializers may map these names to the repository's established API convention, but that mapping MUST be explicit, versioned, and tested. A derived quotation/excerpt is returned alongside the span, not stored as a `SourceSpan` field, and MUST be recomputed from the immutable source.

| Field | Requirement |
|---|---|
| source_id | Required; equals the run source ID. |
| source_version | Required; equals the run immutable source version. |
| start | Required non-negative integer; zero-based and inclusive. |
| end | Required integer greater than `start`, exclusive, and no larger than the source length under the documented character-indexing convention. |

### EvidenceFinding

| Field | Requirement |
|---|---|
| claimId | Required stable claim identifier, unique in submitted claim set. |
| status | Required EvidenceStatus; exactly one primary value. |
| explanation | Required concise human-readable basis. |
| sourceSpans | Required array; non-empty for supported, contradicted, and uncertain; may be empty only for unsupported. Optional unsupported context spans are allowed only as one-to-one pairs with `CONTEXT_NON_SUPPORTING` evidence quotations. |
| evidenceQuotes | Required source-derived quotations paired one-to-one with spans. For an unsupported context span, the quotation MUST be marked `CONTEXT_NON_SUPPORTING` and cannot be presented as support or conflict. |
| discrepancies | Required structured array, with types such as NEGATION, CERTAINTY, ATTRIBUTION, CLINICAL_INFERENCE, and OTHER. |
| policyVersion | Required canonical `EVIDENCE_ANNOTATION-v1` version for every finding. |
| verifierFinding | Retained normalized verifier recommendation when semantic verification was invoked. It MUST remain available if deterministic checks resolve the public status differently. |
| deterministicRuleFindings | Structured deterministic check results, including conflicts with the verifier recommendation; they MUST NOT be silently discarded. |

### VerificationRun

| Field | Requirement |
|---|---|
| verificationRunId | Unique immutable run ID. |
| source_id, source_version | Exact evidence snapshot. |
| noteId, noteRevision | Exact candidate note revision. |
| claimSetId | Exact immutable Spec 003 `extractionRunId` that owns the submitted claims. |
| status | Successful only when all validation and verification obligations complete. |
| findings | Present only for successful run; one finding for each and only each submitted valid claim. |
| failure | Present for non-success; structured failure code and safe diagnostic detail. |
| verifier | Model ID/version and prompt version. |
| annotationPolicyVersion | Classification policy in force. |
| evidenceStatusPolicyVersion | Version of the definitions and precedence for the four primary evidence statuses. |
| idempotencyKey | Required request identity used to make retries resolve to the same run. |
| modelId, modelVersion, promptVersion | Configured verifier identity and prompt version/hash; explicitly null only when unavailable before invocation. |
| inputDigest, promptHash, executionTraceId | Input identity digest, prompt hash, and durable execution-trace identifier for replay and evaluation handoff. |
| correlationId | Required execution trace identifier. |
| createdAt, startedAt, completedAt | Required lifecycle timestamps for durable execution traceability. |

The executable HTTP schema is [contracts/verification-runs.openapi.yaml](contracts/verification-runs.openapi.yaml). It defines success/failure exclusivity and makes `UNSUPPORTED` with no source spans a successful finding, while invalid required spans produce a non-successful `FAILED_EVIDENCE_INTEGRITY` run.

`claimSetId` is the immutable Spec 003 `extractionRunId`. `idempotencyKey` is bound atomically to a canonical digest of the immutable request identity. Repeating the same key with the same digest returns the original run; repeating it with a different digest returns HTTP `409 IDEMPOTENCY_KEY_CONFLICT` and does not start another verification attempt.

## API

### POST /api/v1/verification-runs

Creates one bounded synchronous run for one source version and candidate note revision. The request identifies source snapshot, note revision, claim set, and immutable claim references. The service resolves those references; it never trusts submitted claim assertion text. HTTP 200 returns the terminal immutable run and either evidence findings or structured failure. The PoC has no HTTP 202 response or polling endpoint. Invalid input, stale provenance, span-integrity errors, and verifier failures return a stable non-success schema and must not imply verification or approval. Any asynchronous replacement requires a separately versioned API contract.

The API neither accepts the candidate note as evidence nor mutates upstream records.

## Acceptance scenarios

| Test ID | Scenario | Expected result |
|---|---|---|
| EV-001 | Faithful paraphrase of a source observation | Supported with valid source grounding. |
| EV-002 | Fabricated symptom absent from source | Unsupported. |
| EV-003 | Explicit contradiction of a symptom | Contradicted with conflicting source span. |
| EV-004 | Negation removed during rewriting | Contradicted; discrepancy identifies negation. |
| EV-005 | Uncertainty turned into certainty | `UNCERTAIN` with a `CERTAINTY` discrepancy under `EVIDENCE_ANNOTATION-v1`; use `CONTRADICTED` only when the source explicitly denies or withholds confirmation. |
| EV-006 | Patient-reported symptom changed to confirmed observation | `UNCERTAIN` with an `ATTRIBUTION` discrepancy under `EVIDENCE_ANNOTATION-v1`; a report alone cannot support confirmed observation. |
| EV-007 | Observation turned into unsupported diagnosis | Unsupported; discrepancy identifies clinical inference. |
| EV-008 | Equivalent German medical and colloquial terms | Supported when material qualifiers remain faithful. |
| EV-009 | Ambiguous transcript meaning | Uncertain with relevant grounding and explanation. |
| EV-010 | Evidence quotation does not match source span | Evidence-integrity failure; run non-successful. |
| EV-011 | Source version mismatch | Verification fails safely; no successful findings. |
| EV-012 | Verifier timeout or malformed response | Verification fails; candidate note remains unapproved. |
| EV-013 | “keine starken Schmerzen” used to support “keine Schmerzen” | `UNCERTAIN` with a `NEGATION` discrepancy and relevant source span; explain partial-negation scope. |
| EV-014 | No pain evidence but claim states pain | Unsupported, not contradicted. |

For EV-013, when the partial-negation span is the only relevant evidence, the required primary status is `UNCERTAIN` with a `NEGATION` discrepancy, as defined by CL-009.

Tests must assert the exact claim ID, primary status, applicable discrepancy type, and valid evidence location—not merely a warning.

## Non-functional requirements

- **Safety:** Invalid provenance, spans, structured output, or claim coverage can never yield a successful result.
- **Semantic and deterministic boundaries:** A configured LLM is the primary semantic verifier and compares complete German claim meaning rather than literal token overlap. Deterministic code independently validates inputs, span integrity, contract shape, status normalization, claim coverage, persistence, and exact numeric/unit rules owned by Spec 005. The local synthetic fallback is conservative, preserves the same four-status contract, and never replaces configured LLM verification.
- **Traceability:** Reproduce each result to exact source snapshot, note revision, immutable claim set, model/prompt, and annotation policy.
- **Privacy:** Send only the minimum required transcript and claim material to an approved semantic verifier, following system data handling rules.
- **Observability:** Expose lifecycle state, safe failure code, model/prompt identity, correlation identifiers, latency, inference cost, token usage, rejection reasons, and warning counts without treating invalid evidence as fact or exposing sensitive text.

## Dependencies and definition of done

Spec 001 supplies immutable source text/version, Spec 002 the immutable note revision, and Spec 003 stable atomic claims. Spec 005 owns numeric/unit mismatches; Spec 006 owns omissions/completeness.

Done means every valid claim reference resolves to its exact immutable claim record and has one status, supported claims have valid grounding, unsupported differs from contradicted, qualifier regressions are covered, invalid provenance and model output cannot succeed, responses are schema-valid and traceable, automated tests pass, a complete versioned development evaluation report is reviewed, and results can be evaluated by the annotated synthetic benchmark in Spec 008. Implementation remains blocked until the independent reviewer approves [checklist.md](checklist.md).
