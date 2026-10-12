# Data Model: Evidence Verification

**Feature ID:** 004-evidence-verification  
**Status:** Normative contract for Spec 004  
**Serialization:** Pydantic v2 models; the HTTP representation uses camelCase aliases. The canonical domain names for a source span remain `source_id`, `source_version`, `start`, and `end`.

## Contract boundary

Spec 004 verifies immutable Spec 003 claim records against exactly one immutable
Spec 001 source transcript version. It consumes the candidate note only to
validate the note revision and claim ownership; neither the candidate note,
other claims, prior verification output, retrieval rankings, nor model memory
may serve as evidence.

The module creates immutable verification runs and their findings. It does not
alter source documents, note revisions, extraction results, or claims. Numeric
and unit validation belongs to Spec 005, completeness to Spec 006, caregiver
approval to Spec 007, and held-out evaluation to Spec 008.

## Versioned enumerations

| Enum | Values | Meaning |
| --- | --- | --- |
| `EvidenceStatus` | `SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNCERTAIN` | The one primary semantic result for a claim in a successful run. Definitions and precedence are versioned as `EVIDENCE_STATUS-v1`. |
| `EvidenceRole` | `SUPPORTING`, `CONFLICTING`, `CONTEXT_NON_SUPPORTING` | The role of a source-derived quotation. `CONTEXT_NON_SUPPORTING` is valid only for optional context on an unsupported finding. |
| `Discrepancy` | `NEGATION`, `CERTAINTY`, `ATTRIBUTION`, `CLINICAL_INFERENCE`, `OTHER` | A material semantic change detected while evaluating the claim; it enriches but never replaces the primary status. |
| `DeterministicRuleOutcome` | `PASS`, `WARNING`, `BLOCKING_FAILURE` | Result of a non-semantic deterministic rule. |
| `VerificationRunStatus` | `RECEIVED`, `VALIDATING`, `VERIFYING`, `SUCCEEDED`, `FAILED_VALIDATION`, `FAILED_EVIDENCE_INTEGRITY`, `FAILED_VERIFIER`, `FAILED_PERSISTENCE` | Lifecycle state. `SUCCEEDED` and all four `FAILED_*` states are terminal; only the latter are failures. |

`EVIDENCE_ANNOTATION-v1` is the required `policyVersion` for every finding and
the required `annotationPolicyVersion` for every run. Changes to either policy
require a new version and regression coverage; historical runs retain the
version under which they were produced.

## Upstream identity references

### `ClaimInput`

`ClaimInput` is a request-side provenance reference, not a mutable claim
payload. Assertion text and normalized semantic attributes are deliberately not
accepted from the caller.

| Field | Required | Constraint |
| --- | --- | --- |
| `claimId` | Yes | Non-empty stable Spec 003 claim identifier. Unique within a request. |
| `residentTestId` | Yes | Non-empty synthetic resident identifier matching `^[A-Za-z0-9][A-Za-z0-9._-]*$`; must not be `UNKNOWN`. |

For each reference, the service resolves the immutable upstream record and
requires its claim ID, `claimSetId`, note ID/revision, and synthetic resident to
match the request and source record exactly. The resolved assertion and
normalized claim attributes, rather than request data, are used for discovery
and semantic verification.

### `VerificationRunRequest`

| Field | Required | Constraint |
| --- | --- | --- |
| `sourceId` | Yes | Non-empty immutable Spec 001 source identifier. |
| `sourceVersion` | Yes | Positive integer; identifies the exact immutable transcript version. |
| `noteId` | Yes | Non-empty Spec 002 note identifier. |
| `noteRevision` | Yes | Positive integer identifying the exact candidate note revision. |
| `claimSetId` | Yes | Non-empty immutable Spec 003 `extractionRunId` that owns every referenced claim. |
| `idempotencyKey` | Yes | Non-empty client retry identity. |
| `claims` | Yes | Non-empty array of distinct `ClaimInput` values. |

The canonical request digest is a SHA-256 digest of source identity, note
identity, claim-set identity, and the claim ID/resident-ID pairs sorted by claim
ID. The idempotency key itself is excluded from that digest. A key is bound
atomically to one digest and one verification run: a matching retry returns the
original durable run; reuse with a different digest produces
`IDEMPOTENCY_KEY_CONFLICT` and creates no run.

## Evidence value objects

### `SourceSpan`

| Field | Required | Constraint |
| --- | --- | --- |
| `source_id` / `sourceId` | Yes | Non-empty; exactly equals the verification run source ID. |
| `source_version` / `sourceVersion` | Yes | Positive integer; exactly equals the run source version. |
| `start` | Yes | Non-negative, zero-based Unicode code-point offset; inclusive. |
| `end` | Yes | Unicode code-point offset; exclusive, greater than `start`, and no greater than the exact immutable source length. |

The immutable transcript is used exactly as stored. Byte offsets, token offsets,
UTF-16 offsets, normalized text, and display-adjusted line endings are not
valid substitutes. `SourceSpan` contains no copied text.

### `EvidenceQuote`

| Field | Required | Constraint |
| --- | --- | --- |
| `span` | Yes | A valid `SourceSpan` for the run source snapshot. |
| `text` | Yes | Non-empty exact source substring at `span`; recomputed and validated from immutable source text. A verifier-supplied quotation is never trusted. |
| `evidenceRole` | Yes | `EvidenceRole`. |

Each evidence quotation has exactly one matching source span and vice versa.
The pair is matched by source ID, source version, start, and end; duplicate
spans are forbidden.

### `VerifierFinding`

The normalized semantic-verifier recommendation retained for traceability.

| Field | Required | Constraint |
| --- | --- | --- |
| `status` | Yes | `EvidenceStatus`. |
| `explanation` | Yes | Non-empty concise explanation. |

### `DeterministicRuleFinding`

| Field | Required | Constraint |
| --- | --- | --- |
| `code` | Yes | Non-empty machine-readable deterministic-rule identifier. |
| `outcome` | Yes | `PASS`, `WARNING`, or `BLOCKING_FAILURE`. |

Deterministic validation owns contract shape, provenance, coverage, span, quote,
and persistence integrity. It does not infer semantic support or contradiction.
If a mechanical rule conflicts with the verifier recommendation, both records
remain available; an invalid successful result fails safely rather than silently
receiving a replacement evidence status.

## `EvidenceFinding`

One `EvidenceFinding` exists for each and only each submitted claim in a
successful run.

| Field | Required | Constraint |
| --- | --- | --- |
| `claimId` | Yes | A submitted, resolved claim ID; unique within the run. |
| `status` | Yes | Exactly one `EvidenceStatus`. |
| `explanation` | Yes | Non-empty concise, reviewer-facing basis. |
| `sourceSpans` | Yes | Source spans paired one-to-one with `evidenceQuotes`; required and non-empty except as noted for `UNSUPPORTED`. |
| `evidenceQuotes` | Yes | Source-derived `EvidenceQuote` values paired one-to-one with `sourceSpans`. |
| `discrepancies` | Yes | Zero or more `Discrepancy` values. |
| `policyVersion` | Yes | Exactly `EVIDENCE_ANNOTATION-v1`. |
| `verifierFinding` | Yes | Normalized semantic-verifier recommendation. |
| `deterministicRuleFindings` | Yes | Zero or more deterministic validation results, retained even on disagreement. |

Finding invariants:

1. `SUPPORTED`, `CONTRADICTED`, and `UNCERTAIN` require at least one valid
   span/quotation pair. `SUPPORTING` and `CONFLICTING` roles are permitted for
   these statuses; `CONTEXT_NON_SUPPORTING` is not.
2. `UNSUPPORTED` may have no evidence pairs. If it has optional contextual
   pairs, every quotation role must be `CONTEXT_NON_SUPPORTING`; such context
   is never presented as support or conflict.
3. A valid span/quotation pair must reference the run's exact source ID and
   version, have `0 <= start < end <= len(source_text)`, and use quotation text
   equal to `source_text[start:end]` under Unicode code-point indexing.
4. A discrepancy explains a material qualifier or inference change but does not
   change status by itself. The semantic decision follows
   `EVIDENCE_ANNOTATION-v1` and `EVIDENCE_STATUS-v1` precedence.

## `VerificationFailure`

| Field | Required | Constraint |
| --- | --- | --- |
| `code` | Yes | Non-empty stable machine-readable failure code. |
| `reason` | Yes | Non-empty safe human-readable diagnostic. Must not expose unvalidated transcript or model content. |

Failure is separate from evidence status. A processing, provenance, schema,
timeout, evidence-integrity, or persistence failure is never represented as
`UNCERTAIN`, `UNSUPPORTED`, or another evidence status.

## `VerificationRun`

The public and persisted record is a discriminated union. Runs are immutable
after their terminal result is durably stored.

### Shared provenance and execution fields

| Field | Required | Constraint |
| --- | --- | --- |
| `verificationRunId` | Yes | Unique immutable run identifier. |
| `sourceId`, `sourceVersion` | Yes | Exact immutable source snapshot. |
| `noteId`, `noteRevision` | Yes | Exact candidate note revision. |
| `claimSetId` | Yes | Immutable Spec 003 `extractionRunId`. |
| `idempotencyKey` | Yes | The atomically bound retry key. |
| `inputDigest` | Yes | Canonical digest of immutable request identity. |
| `evidenceStatusPolicyVersion` | Yes | Exactly `EVIDENCE_STATUS-v1`. |
| `annotationPolicyVersion` | Yes | Exactly `EVIDENCE_ANNOTATION-v1`. |
| `modelId`, `modelVersion` | Yes | Configured verifier identity/version; may be `null` only when unavailable before invocation. Must be non-null for success. |
| `promptVersion`, `promptHash` | Yes | Prompt identity/version and immutable hash; may be `null` only when unavailable before invocation. Must be non-null for success. |
| `correlationId` | Yes | Non-empty trace/correlation identifier. |
| `executionTraceId` | Yes | Non-empty durable trace identifier connecting verification, validation, and persistence. |
| `createdAt`, `startedAt`, `completedAt` | Yes | Timezone-aware lifecycle timestamps satisfying `createdAt <= startedAt <= completedAt`. |
| `status` | Yes | `VerificationRunStatus`. |

The persistence model may additionally retain a source-content digest from Spec
001, token/cost/latency telemetry, rejection and warning counts, and redacted
provider diagnostics. These supplement, but cannot replace, required source
ID/version provenance or the immutable public run contract.

### `VerificationRunSucceeded`

| Field | Required | Constraint |
| --- | --- | --- |
| `status` | Yes | Exactly `SUCCEEDED`. |
| `findings` | Yes | Non-empty array of `EvidenceFinding`; its distinct claim IDs equal the submitted claim-ID set exactly. |

`failure` is forbidden. A successful run has complete validated coverage: no
missing, duplicate, foreign, or partially authoritative findings are allowed.

### `VerificationRunFailed`

| Field | Required | Constraint |
| --- | --- | --- |
| `status` | Yes | One of `FAILED_VALIDATION`, `FAILED_EVIDENCE_INTEGRITY`, `FAILED_VERIFIER`, or `FAILED_PERSISTENCE`. |
| `failure` | Yes | `VerificationFailure`. |

`findings` is forbidden. An identifiable request that fails after processing
begins is retained as a durable failed run; malformed HTTP payloads that cannot
form a run may instead receive the standard API validation error envelope.

## Lifecycle and persistence

```text
RECEIVED -> VALIDATING -> VERIFYING -> SUCCEEDED
                       \-> FAILED_VALIDATION
                                     \
VERIFYING ---------------------------> FAILED_VERIFIER
VERIFYING / integrity validation ----> FAILED_EVIDENCE_INTEGRITY
any durable-write failure ------------> FAILED_PERSISTENCE
```

The local PoC uses SQLite behind a repository abstraction. The database or
transaction boundary enforces these uniqueness rules:

- one immutable record per `verificationRunId`;
- one finding per `(verificationRunId, claimId)`;
- one idempotency key bound to exactly one `inputDigest` and run;
- atomic persistence of the run payload and its idempotency association.

For a successful run, the parent record and all child findings, spans,
quotations, verifier recommendations, and deterministic-rule findings are
persisted atomically (or as an immutable equivalent). A failed run persists no
authoritative findings but retains its provenance, execution metadata, terminal
status, and safe failure record.

## Cross-model invariants

1. The source transcript is the sole evidence authority, and every evidence
   reference resolves to the exact immutable `(sourceId, sourceVersion)`.
2. Every submitted claim resolves from the requested immutable claim set and
   belongs to the requested note revision; its resident matches both the source
   and the request. No resident is inferred or disambiguated.
3. A successful run provides exactly one complete, validated primary finding
   for every submitted claim and no other claim.
4. Evidence quotations are derived from source spans and never independently
   trusted, stored as primary authority, or repaired silently.
5. An invalid source reference, span, quotation, claim coverage, verifier
   response, or persistence operation cannot yield a successful run.
6. `UNSUPPORTED` with no span is a valid semantic result; an invalid required
   span is an evidence-integrity failure, not an unsupported result.
7. The idempotency key replay rule prevents duplicate semantic verification for
   the same request and rejects reuse for a different request before invocation.
8. Model/prompt identity, policy versions, timestamps, correlation ID, and
   execution trace ID remain attached to every durable run for replay and
   evaluation handoff.

The executable HTTP shape, including success/failure exclusivity, is defined in
[verification-runs.openapi.yaml](contracts/verification-runs.openapi.yaml).
