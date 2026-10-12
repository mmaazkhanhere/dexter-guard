# Spec 007 Data Model

**Contract version:** `REVIEW-AUDIT-CONTRACT-v1`  
**Severity policy:** `REVIEW_SEVERITY-v1`  
**Persistence rule:** All review-owned records are immutable/append-only. Upstream source, note, claim, and verification records retain their existing ownership.

## Reused immutable references

| Reference | Owner | Required identity |
| --- | --- | --- |
| Source snapshot | Spec 001 | `sourceId`, `sourceVersion`, source text hash, normalization policy |
| Note revision | Spec 002 | `noteId`, positive `revision`, immutable content and source reference |
| Claim/claim set | Spec 003 | `claimId`, `claimSetId`/extraction run, exact note revision |
| Evidence run/finding | Spec 004 | `verificationRunId`, `claimId`, evidence status and valid spans/quotes |
| Validation run/finding | Spec 005 | `validationRunId`, rule ID/finding identity, exact note/source references |
| Coverage run/finding | Spec 006 | `coverageRunId`, coverage finding identity, exact note/source references |

## Entities

### `ReviewFinding`

Normalized read/persistence record representing an upstream finding or a review-created operational finding. It does not replace the upstream artifact.

| Field | Required | Constraints |
| --- | --- | --- |
| `reviewFindingId` | Yes | Stable ID; immutable. |
| `origin` | Yes | `SPEC_004`, `SPEC_005`, `SPEC_006`, or `REVIEW_OPERATIONAL`. |
| `originRunId`, `originFindingId` | Upstream | Both required for upstream finding; null only for operational finding. |
| `noteId`, `noteRevision` | Yes | Exact immutable note revision. |
| `sourceId`, `sourceVersion` | Yes | Must equal the note revision's evidence source. |
| `claimId` | No | Required where upstream finding is claim-level; absent for source-only coverage/operational finding. |
| `upstreamStatus`, `ruleCode` | As applicable | Preserved, never reclassified. |
| `severity` | Yes | `CRITICAL`, `MAJOR`, `MINOR`; assigned once by `REVIEW_SEVERITY-v1`. |
| `severityPolicyVersion`, `severityRationale` | Yes | Version and deterministic mapping explanation. |
| `explanation` | Yes | Reviewer-facing, origin-provided/derived safe text. |
| `evidenceAvailability` | Yes | `AVAILABLE`, `MISSING`, `INVALID`; only `AVAILABLE` exposes valid display spans. |
| `evidenceSpans`, `evidenceExcerpts` | Yes | Pairwise derived from exact source only when availability is `AVAILABLE`; empty otherwise. |
| `createdAt` | Yes | Timezone-aware timestamp. |

Constraint: a missing span allowed by an upstream `UNSUPPORTED` result maps to `MISSING`, not `INVALID`; an invalid/mismatched supplied reference maps to `INVALID` and creates/retains a critical integrity condition.

### `ReviewDecision`

An immutable human event about one `ReviewFinding` on one note revision.

| Field | Required | Constraints |
| --- | --- | --- |
| `reviewDecisionId`, `findingId`, `noteId`, `noteRevision` | Yes | References must match finding identity. |
| `kind` | Yes | `ACKNOWLEDGED`, `DISPUTED`, `ADJUDICATED`, `MANUAL_CORRECTION_RECORDED`, `SUGGESTION_ACCEPTED`, `SUGGESTION_REJECTED`. |
| `outcome` | Yes | `NO_STATE_CHANGE`, `OPEN`, `ADJUDICATED`, `RESOLVED`, `STALE`; allowed combinations validated by policy. |
| `reviewerLabel`, `recordedAt` | Yes | Non-blank synthetic label; timezone-aware time. |
| `rationale` | Conditional | Required for `DISPUTED`, `ADJUDICATED`, and suggestion rejection; optional for acknowledgement. |
| `successorRevision`, `suggestionId` | Conditional | Required for correction/accepted-suggestion records as applicable. |
| `idempotencyKey` | Yes | Atomically bound to canonical decision command digest. |

Decision commands carry `expectedRevision` (compare-and-swap), not a client-selected
`noteRevision`. The server resolves the current revision inside the write transaction and
records that resolved value in `ReviewDecision.noteRevision`; a mismatch returns
`409 STALE_REVISION` without appending a decision or audit event.

### `SuggestedCorrection`

| Field | Required | Constraints |
| --- | --- | --- |
| `suggestionId`, `findingId`, `noteId`, `baseRevision` | Yes | Bound to one immutable finding/revision. |
| `replacement`, `targetNoteSpan` | Yes | Non-empty replacement and valid exact candidate-note target span. |
| `supportSpans` | Yes | One or more exact source spans required for `USABLE`; derived excerpts retained only with references. |
| `supportStatus` | Yes | `USABLE`, `UNUSABLE`, `REJECTED`; unsupported/invalid never `USABLE`. |
| `generatedBy` | Yes | `REVIEWER` or a versioned Spec 007 correction adapter. Raw `SPEC_006` suggestion strings remain display-only and cannot be persisted as `USABLE` corrections. |
| `createdAt`, `acceptedDecisionId`, `rejectedDecisionId` | Yes/conditional | Immutable lifecycle references; at most one terminal acceptance/rejection. |

### `FullNoteVerification`

| Field | Required | Constraints |
| --- | --- | --- |
| `fullVerificationId`, `requestDigest`, `idempotencyKey` | Yes | Immutable identity; key is one-to-one with digest. |
| `noteId`, `noteRevision`, `sourceId`, `sourceVersion` | Yes | Exact immutable binding, equal to all valid components. |
| `claimSetId` | Yes | Exact current Spec 003 extraction run. |
| `evidenceRunId`, `deterministicValidationRunId`, `coverageRunId` | Yes | Required component run IDs; may not refer to another revision/source. |
| `status` | Yes | `VALID`, `INVALID`, or `FAILED`; every persisted aggregate is terminal and immutable. A valid empty Spec 003 claim set is `INVALID` with `EMPTY_CLAIM_SET_REQUIRES_REVIEW`. |
| `componentStatuses` | Yes | Exactly one status for each of CLAIM_EXTRACTION, EVIDENCE_VERIFICATION, DETERMINISTIC_VALIDATION, and SOURCE_COVERAGE; aggregate `VALID` requires all four `SUCCEEDED` and reference validation. |
| `createdAt`, `completedAt`, `correlationId` | Yes | Lifecycle/audit fields; terminal timestamp required for terminal state. |
| `failureCode`, `failureMessage` | Conditional | Required for `INVALID`/`FAILED`; contains safe diagnostic only. |

The synchronous endpoint does not expose or persist a non-terminal aggregate. A client sees only a terminal `VALID`, `INVALID`, or `FAILED` result; an upstream operation that fails after starting is retained as a terminal failed/invalid aggregate.

### `NoteDisposition`

| Field | Required | Constraints |
| --- | --- | --- |
| `dispositionId`, `noteId`, `noteRevision` | Yes | One immutable human disposition event. |
| `kind` | Yes | `APPROVED` or `REJECTED`. |
| `reviewerLabel`, `decidedAt`, `reason` | Yes | Reason non-empty for rejection; approval rationale optional/recorded if supplied. |
| `fullVerificationId` | Approved | Required and must be `VALID` for same note/revision/source. |
| `eligibilityPolicyVersion` | Approved | `REVIEW_APPROVAL-v1`; evaluated atomically. |

### `AuditEvent`

| Field | Required | Constraints |
| --- | --- | --- |
| `eventId`, `sequence`, `occurredAt`, `actorLabel`, `eventType` | Yes | Sequence monotonic per note; append-only. |
| `noteId`, `noteRevision` | Yes | Stable target identity. |
| `targetType`, `targetId`, `references` | Yes | References include prior/successor revision, finding, run, decision, suggestion, or disposition as applicable. |
| `payloadDigest` | Yes | Tamper-evidence aid; do not duplicate full note/source bodies. |
| `rationale` | Conditional | Required where the source event requires rationale. |

## State-transition tables

### Note status (latest revision projection)

| From | Event / guard | To |
| --- | --- | --- |
| `DRAFT` | Review context opened | `IN_REVIEW` |
| `IN_REVIEW` | Save successor revision or accept suggestion | successor `AWAITING_FULL_VERIFICATION`; predecessor remains historical |
| `AWAITING_FULL_VERIFICATION` | Valid full-note verification + policy decision completeness | `ELIGIBLE_FOR_APPROVAL` |
| `AWAITING_FULL_VERIFICATION` | Full verification invalid/failed | `IN_REVIEW` with blocking operational finding |
| `ELIGIBLE_FOR_APPROVAL` | Any new revision/changed latest identity | successor `AWAITING_FULL_VERIFICATION` |
| `ELIGIBLE_FOR_APPROVAL` | Atomic approval guard passes | `APPROVED` |
| any non-final latest revision | Human rejection with reason | `REJECTED` |
| `APPROVED` or `REJECTED` | Any revision-save command | Rejected with `FINAL_DISPOSITION_IMMUTABLE`; reopening is out of scope for this feature |

### Finding status

| From | Event / guard | To |
| --- | --- | --- |
| `OPEN` | Acknowledged | `OPEN` |
| `OPEN` | Disputed with rationale | `OPEN` |
| `OPEN` non-critical | Valid documented adjudication | `ADJUDICATED` or `RESOLVED` |
| `OPEN` critical | Acknowledged/disputed/adjudicated | `OPEN` |
| `OPEN` | Successor note revision created | `STALE` for approval |
| `OPEN`/`ADJUDICATED` non-critical | Later valid full-note run no longer emits equivalent issue | `RESOLVED` |
| `STALE` | Historical display | `STALE` (never silently reopened for successor) |

### Verification aggregate status

| From | Event | To |
| --- | --- | --- |
| request execution | All required exact-revision components succeed and validate | `VALID` |
| request execution | Any component fails/is unavailable/malformed | `FAILED` |
| request execution | Component source/note/claim provenance or output closure fails | `INVALID` |
| terminal | Any retry | new aggregate or idempotent replay; never mutate terminal record |

## Database invariants

1. `(note_id, revision)` is unique and revisions are append-only; successor revision equals predecessor plus one.
2. Every review-owned record references an existing immutable note revision, and its source pair equals the revision source pair.
3. Every evidence span is either validated against the exact immutable source before display or represented as unavailable; no unvalidated quote is authoritative.
4. Candidate note spans identify candidate content only and cannot populate source evidence fields.
5. A decision cannot cross note/revision/finding identity boundaries; required rationales are non-blank.
6. A suggestion cannot be accepted if its base revision is stale, its support is not `USABLE`, or its target span no longer applies exactly.
7. `VALID` full verification has exactly one successful, provenance-consistent component reference for 004, 005, and 006 and its exact current claim set. A successful Spec 006 run with any unresolved source item is not approval-valid.
8. Approval has one valid same-revision full verification, passes eligibility atomically, and cannot coexist with a competing approval for the same revision.
9. Rejection is permitted without a valid full verification but requires a reason.
10. Existing audit records, prior note revisions, upstream runs/findings, and decisions are never overwritten or deleted by review actions.
