# Feature Specification: Human Review and Audit

**Feature ID:** 007-human-review-and-audit  
**Status:** Draft — requirements-quality review required before implementation  
**Constitution baseline:** AI Nursing Documentation Reliability Engine Constitution v1.0.0

## Goal and purpose

Provide a human-in-the-loop workflow in which a reviewer can inspect, correct, re-verify, approve, or reject an AI-generated German nursing note for one synthetic resident. The workflow converts findings from evidence verification, deterministic validation, and source coverage into traceable human decisions. It verifies documentation fidelity to the immutable transcript; it does not determine medical truth or make a clinical decision.

The approval gate is deliberately fail-closed: an outdated, incomplete, failed, malformed, or source-mismatched verification result cannot authorize approval.

## Scope and boundaries

This feature owns the review presentation, severity policy, finding-level decisions, immutable reviewer-created note revisions, review orchestration, approval/rejection policy, and append-only audit history. It consumes immutable source, note, claim, evidence-verification, deterministic-validation, and coverage artifacts; it does not recreate their algorithms or silently alter their results.

The PoC uses synthetic German nursing documentation only, one resident per transcript, a desktop-oriented interface, FastAPI/Pydantic contracts, and the repository persistence technology. Reviewer labels are sufficient attribution; this feature introduces neither authentication nor roles.

### Explicit non-goals

- Medical diagnosis, treatment recommendation, or adjudication of clinical truth.
- Real patient or employee data, EHR integration, or regulatory-certification claims.
- Audio input, speech recognition, multi-resident identification, mobile interface, microservices, queues, or model training.
- Reimplementing claim extraction, evidence comparison, numeric/unit validation, or source-coverage algorithms.
- Automatic correction, automatic approval, or treating the candidate note as its own evidence.

## Dependencies and ownership

| Dependency | Consumed by this feature | Boundary |
| --- | --- | --- |
| Spec 001 source and note ingestion | Immutable `SourceDocument`, `SourceSpan`, source hash/version and Unicode offset semantics | Spec 007 resolves evidence only against the exact source version; it never changes source text. |
| Spec 002 nursing-note generation | Immutable `NoteRevision` identity, content, origin, source reference, revision lineage | Spec 007 creates successor revisions through the note-revision boundary; it does not mutate existing revisions. |
| Spec 003 claim extraction | Immutable claim-set/extraction run, claim IDs, note text spans, source provenance | Required before claim-level or full-note verification; a new revision requires a new extraction result. |
| Spec 004 evidence verification | Evidence findings and terminal verification runs | Owns support/contradiction/uncertainty classification and source-span/quotation integrity. |
| Spec 005 deterministic validation | Validation findings/runs | Owns numeric, unit, structural, and evidence-reference rules; Spec 007 assigns severity only. |
| Spec 006 source coverage | Coverage findings/runs and suggestions | Owns source-to-note completeness assessment; Spec 007 assigns final severity and never changes assessment results. |

The review-facing claim-extraction invocation, the Spec 005 source-fact/alignment adapter, and the atomic full-note orchestration boundary are planned integration work, not existing public contracts. Their feature-local decisions are defined in this specification and plan; implementation must not substitute a prose-parsing or algorithm-duplicating workaround.

## Reviewer user stories

### P1 — Inspect an evidence-grounded finding

As a reviewer, I want to select a finding and see the affected candidate claim, its explanation, severity, and the exact transcript evidence where valid, so I can make an informed documentation decision.

**Independent test:** A synthetic German note with a source-linked finding reveals the exact claim and derived source excerpt; an invalid/missing source span is visibly labelled unavailable and does not highlight unrelated text.

### P1 — Correct and re-verify a note

As a reviewer, I want to accept a source-grounded suggestion or manually correct a note, then re-verify it, so a later decision is based on the edited text rather than an obsolete result.

**Independent test:** An accepted suggestion and a manual edit each create an immutable successor revision, make old runs stale for approval, and require verification of the successor.

### P1 — Safely approve or reject

As a reviewer, I want approval to be blocked until the latest complete note is validly verified and critical discrepancies are resolved, while still being able to reject an unsafe note when verification fails.

**Independent test:** Direct API approval fails for a stale revision, missing/full-note-failed verification, invalid output, or unresolved critical finding; rejection succeeds with a reason.

### P2 — Record independent finding decisions

As a reviewer, I want to acknowledge, dispute with rationale, or adjudicate individual findings without losing their original result, so the reasoning is auditable.

**Independent test:** A non-critical finding can receive the documented decision path; acknowledgement records review but does not clear a critical discrepancy.

### P2 — Inspect an audit trail

As a reviewer, I want to view original and corrected note revisions, runs, suggestions, decisions, and final disposition in sequence, so I can reconstruct why a note was approved or rejected.

**Independent test:** Audit history returns immutable original and successor revision records with reviewer labels, timestamps, rationales, and stable references.

### P3 — Use a suggested correction safely

As a reviewer, I want optional proposed wording that remains visibly source-grounded and requires explicit acceptance, so I retain authority over any change.

**Independent test:** A suggestion with no valid source support is rejected or shown unusable; accepting a valid suggestion never edits in place.

## Functional requirements

| ID | Requirement | Owner | Acceptance scenarios |
| --- | --- | --- |
| FR-15 | Assign every review finding exactly one `CRITICAL`, `MAJOR`, or `MINOR` severity using `REVIEW_SEVERITY-v1`, a deterministic policy based on imported status/rule/policy metadata rather than an LLM label. Preserve upstream results unchanged. | Review policy | HR-001, HR-013, HR-014 |
| FR-17 | Display the current immutable transcript, current candidate note, claim locations, valid evidence references, severity, human-readable explanations, suggestions, decisions, and note status. Selecting a finding reveals its affected claim and evidence where available. | Review context/read model | HR-001, HR-002 |
| FR-18 | Record independent finding-level decisions: accepted suggestion, manual correction reference, acknowledgement, dispute with rationale, and adjudication. Acknowledgement alone never resolves a critical discrepancy. | Finding decision service | HR-003, HR-013 |
| FR-19 | Permit a reviewer-labelled manual note correction only by creating a new immutable revision; retain all earlier revisions and decision history. | Revision service | HR-004, HR-005, HR-017 |
| FR-20 | Present optional suggested corrections only when they are source-grounded and explicitly accepted; acceptance creates a successor revision. Unsupported suggestions are unusable and cannot be applied. | Suggestion service | HR-004, HR-003 |
| FR-21 | Trigger claim-level re-verification for feedback using the exact source and note revision. It may update review feedback but cannot satisfy final approval. | Claim re-verification orchestrator | HR-006 |
| FR-22 | Trigger and retain a full-note verification of the latest complete revision, including the established evidence verification, deterministic validation, and coverage checks, each bound to that source version and revision. | Full-note verification orchestrator | HR-007, HR-016 |
| FR-23 | Backend approval eligibility must block any approval with an unresolved critical discrepancy, including a critical operational/integrity finding. | Approval policy | HR-008, HR-014 |
| FR-24 | Record human approval, rejection, and documented adjudication. Approval is allowed only under the policy; rejection remains available even after verification failure. | Disposition service | HR-008, HR-009, HR-015 |
| FR-25 | Preserve an append-only, traceable history of original candidate notes, revisions, runs/findings, reviewer decisions, suggestions, and dispositions with reviewer label, timestamp, references, and rationale where required. | Audit service/repository | HR-010, HR-017 |

## Business rules and review lifecycle

### States are separate

- A **note status** is `DRAFT`, `IN_REVIEW`, `AWAITING_FULL_VERIFICATION`, `ELIGIBLE_FOR_APPROVAL`, `APPROVED`, or `REJECTED`. Status describes the latest revision only and never rewrites history.
- A **finding status** is `OPEN`, `RESOLVED`, `ADJUDICATED`, or `STALE`. It is tied to an immutable finding and the revision it assessed.
- An upstream **verification-run status** stays owned by Specs 004–006 (`SUCCEEDED`/their documented terminal failure values). A failed run is not an evidence status and cannot be represented as `UNSUPPORTED` or `UNCERTAIN`.

### Severity policy (`REVIEW_SEVERITY-v1`)

Severity is a documentation-fidelity priority, not a medical risk judgement. The policy maps each incoming finding deterministically in this order:

1. Evidence-integrity/provenance failures (`EVD-001`–`EVD-003`, source-version/hash/quotation mismatch, invalid claim or span) and any terminal full-note component failure are **CRITICAL** operational findings.
2. Spec 004 `CONTRADICTED` is **CRITICAL**. `UNSUPPORTED` and `UNCERTAIN` are **MAJOR**.
3. Spec 005 `FAIL` outcomes other than the evidence-integrity rules and `NOT_EVALUABLE` outcomes are **MAJOR**; explicitly non-blocking informational rule warnings, if introduced by a versioned upstream contract, are **MINOR**.
4. Spec 006 findings retain their producer policy keys and Spec 007 maps the current `COVERAGE_EXPECTATION-v1` keys deterministically: `MEASUREMENT_OMISSION` → **CRITICAL**; `SYMPTOM_OMISSION`, `MOBILITY_ASSISTANCE_OMISSION`, `CARE_ACTION_OMISSION`, and `UNCERTAINTY_OMISSION` → **MAJOR**. An unrecognised or absent key is **MAJOR** for `MISSING`, `DISTORTED`, or `UNCERTAIN`, and **MINOR** only for a future explicitly informational coverage finding. Spec 007 severity labels are never sent back as Spec 006 policy keys.
5. Any new/unknown upstream finding type is **CRITICAL** until `REVIEW_SEVERITY-v1` is revised and approved. This is a fail-safe compatibility rule, not an interpretation of the finding.

The current Spec 006 contract permits a free-form optional `severityPolicyKey`; the current omission keys and their mapping above are the reviewed v1 vocabulary. Ambiguous clinical importance is not inferred by a model. An unknown producer key follows the conservative fallback and requires a policy update before it can receive a lower severity.

### Finding decisions

- New imported findings are `OPEN`.
- A valid accepted suggestion or manual edit creates a new revision; all findings attached to the predecessor become `STALE` for approval, while their decision events remain immutable.
- Spec 006 `CoverageFinding.suggestion` is a source-derived display aid only under CL-014. It cannot be accepted directly. A separate `SuggestedCorrection` is `USABLE` only after Spec 007 validates a target note span, replacement text, and source support; otherwise it remains `UNUSABLE`.
- An `ACKNOWLEDGED` decision records that a reviewer saw a finding but leaves it `OPEN`.
- A `DISPUTED` decision requires non-blank rationale and leaves the finding `OPEN` until an adjudication records a decision.
- An `ADJUDICATED` decision requires non-blank rationale, reviewer label, and an allowed outcome. It may set a non-critical finding to `ADJUDICATED`/resolved for that revision; it cannot resolve a critical evidence/integrity blocker without a later successful full-note verification of a successor/current revision. A critical finding cannot be cleared merely by acknowledgement, dispute, or adjudication.
- `RESOLVED` means a later successful full-note verification of the current revision no longer produces the equivalent issue, or the documented non-critical adjudication policy permits it. It never mutates an upstream run or its original finding.

### Revisions and concurrency

Saving text or accepting a suggestion requires `expectedRevision`, creates exactly `revision + 1`, and atomically appends the revision plus its audit event. The server rejects a stale/current-version mismatch with `409 STALE_REVISION`; it never merges text or overwrites a revision. A saved successor is `AWAITING_FULL_VERIFICATION`; old claim sets and runs remain available only as history and are ineligible for approval. “Saved” is not “verified.”

### Verification and approval rules

Claim-level verification is a narrow feedback operation and must retain the exact source/version, note revision, claim-set ID, and upstream run reference. It cannot create `ELIGIBLE_FOR_APPROVAL`.

A full-note verification bundles fresh/exact upstream runs for **all claims of the current revision**: Spec 004 evidence verification, Spec 005 deterministic validation (where its documented aligned inputs are available), and Spec 006 source coverage. Every component must complete with a valid terminal success result for the same `(sourceId, sourceVersion, noteId, revision)` and expected immutable input identities. Its aggregate is invalid if a required component fails, is malformed, incomplete, source-mismatched, or references a different revision.

The backend may approve only when, in one database transaction/compare-and-swap operation:

1. the submitted revision is still the latest revision for the note;
2. the source ID/version still equals that revision's immutable evidence source;
3. the referenced full-note verification is `VALID`, complete, and binds to that exact revision and source;
4. no `OPEN` or `STALE` critical finding remains for that revision, and no current critical operational verification finding exists;
5. all policy-required decision/adjudication records are complete; and
6. no verification component is failed, invalid, or incomplete.

A successful Spec 006 run containing any unresolved source item (`unresolvedSourceItems > 0` or an unresolved-item `UNCERTAIN` assessment) is never approval-eligible, even if runtime completeness is high or a reviewer records acknowledgement/adjudication. A later full-note run must resolve the source item before approval.

The transaction writes the approval disposition and audit event only if the checks and latest-revision predicate still hold. A concurrent edit therefore makes approval fail with `409 STALE_REVISION`/`APPROVAL_PRECONDITION_FAILED`, not approve an earlier revision. Rejection requires only the current revision reference, reviewer label, and reason; it remains possible after verification failure.

## Acceptance scenarios

All scenarios use synthetic German nursing documentation and synthetic resident IDs only.

| ID | Given / When / Then |
| --- | --- |
| HR-001 | **Given** an evidence finding with a valid Spec 003 claim span and a valid Spec 001 source span, **when** the reviewer selects it, **then** the review context shows the exact affected candidate claim, derived transcript excerpt, status, explanation, and deterministic severity. |
| HR-002 | **Given** an unsupported finding with no evidence span, or a finding with invalid/mismatched span data, **when** it is displayed, **then** the UI labels evidence as unavailable/invalid and shows no contradiction or fabricated highlight. |
| HR-003 | **Given** an open finding, **when** a reviewer acknowledges it, disputes it with a reason, accepts a valid suggestion, or records an adjudication, **then** an immutable decision event retains reviewer label, timestamp, rationale where required, revision, and finding reference; acknowledgement does not clear a critical issue. |
| HR-004 | **Given** a source-grounded suggested correction, **when** the reviewer explicitly accepts it using the current revision, **then** the server creates one immutable successor revision and marks predecessor runs/findings stale for approval. |
| HR-005 | **Given** a reviewer manually changes a note, **when** the save uses the current expected revision, **then** old verification results become stale; **when** another update already created a successor, **then** the save returns `409 STALE_REVISION` and writes nothing. |
| HR-006 | **Given** an edited claim, **when** claim-level re-verification completes successfully for that claim and revision, **then** feedback is updated but approval remains blocked until a valid full-note verification exists. |
| HR-007 | **Given** revision 2 is the latest note after revision 1 was fully verified, **when** final verification is requested, **then** the orchestrator evaluates revision 2 with all required components and cannot use revision 1 runs. |
| HR-008 | **Given** the latest revision has an open critical discrepancy, **when** an API client attempts approval directly, **then** the backend rejects it with `409 APPROVAL_PRECONDITION_FAILED` and records no approval. |
| HR-009 | **Given** full-note verification has failed, **when** a reviewer rejects the latest note with a reason, **then** rejection is recorded successfully and remains auditable. |
| HR-010 | **Given** an original candidate, a corrected successor, review decisions, and verification runs, **when** audit history is requested, **then** it returns all immutable records in event order without replacing original content or prior decisions. |
| HR-011 | **Given** a suggestion whose proposed text contains a fact unsupported by its declared source evidence, **when** it is received or selected, **then** it is marked `UNUSABLE`/rejected and cannot be applied. |
| HR-012 | **Given** a finding span references a different immutable source version, **when** review context is assembled, **then** it is rejected/reported as invalid and cannot support a highlight or approval. |
| HR-013 | **Given** a non-critical finding, **when** a reviewer disputes it and an adjudicator records the required rationale under the policy, **then** the finding follows the documented adjudication transition without changing upstream output. |
| HR-014 | **Given** a malformed, incomplete, or failed verification component, **when** approval is attempted, **then** the backend blocks approval regardless of UI state. |
| HR-015 | **Given** a stale revision or a concurrent edit between eligibility evaluation and approval, **when** approval is requested, **then** atomic comparison fails and no approval is written. |
| HR-016 | **Given** a fully corrected synthetic German note and valid successful components for its latest revision/source, **when** all policy-required decisions are complete and approval is requested, **then** it is approved and audit history contains the disposition. |
| HR-017 | **Given** a full-note verification succeeds, **when** the note is edited afterward, **then** its status returns to `AWAITING_FULL_VERIFICATION` and a new full-note verification is required before approval. |
| HR-018 | **Given** a successful Spec 006 run contains an unresolved source item, **when** approval is attempted, **then** the backend blocks approval regardless of runtime completeness or finding acknowledgement/adjudication. |

## Edge cases and failure behaviour

- Missing claim spans, missing source spans, invalid offsets, text mismatches, or source-version mismatches are visible integrity failures; no fallback search/highlight is attempted.
- `UNSUPPORTED` means no source support was established; it is not displayed as a direct contradiction.
- Source excerpts are always derived from validated `SourceSpan`; candidate note text is never evidence for itself.
- A failed upstream run produces an explicit critical operational review finding and preserves the upstream failure record; it never creates partial authoritative findings.
- A malformed suggestion, stale decision command, unknown finding, foreign note/revision reference, or duplicate idempotency key returns a typed error and writes no partial event.
- A source revision after note creation does not silently retarget the note. The note remains tied to its existing source version; any source migration is outside this feature.

## Measurable success criteria

- Every FR-15 and FR-17–FR-25 maps to at least one acceptance scenario, contract operation, and planned task.
- 100% of approval test attempts with stale, failed, invalid, incomplete, source-mismatched, or critical-open verification inputs are rejected by the backend.
- 100% of accepted edits/suggestions create a new immutable revision; historical revisions and decisions remain retrievable.
- 100% of rendered evidence excerpts in acceptance tests are derived from valid spans for the exact immutable source version; invalid/missing spans show no misleading highlight.
- Synthetic German acceptance fixtures cover HR-001 through HR-018, including direct API guard-bypass attempts and unresolved-source-item blocking.

## Assumptions and resolved integration decisions

1. The existing single-process FastAPI application is the integration host; a React application boundary exists only as a target architecture, not as an inspected implementation in this repository.
2. Spec 006 keys are mapped by `REVIEW_SEVERITY-v1` as documented: `MEASUREMENT_OMISSION` is critical; symptom, mobility, care-action, and uncertainty omission keys are major; all other values follow conservative fallback behaviour.
3. A Spec 005-owned reference-only deterministic-validation adapter resolves existing immutable source facts and explicit alignments; Spec 007 does not create them.
4. The local PoC uses in-process claim extraction, not a new public endpoint.
5. The review repository uses idempotent local SQLite schema initialization without introducing a migration dependency. A valid empty claim set blocks approval as `EMPTY_CLAIM_SET_REQUIRES_REVIEW`.
