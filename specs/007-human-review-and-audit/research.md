# Spec 007 Research and Decision Record

This record captures design decisions based on repository contracts and architecture review. It does not claim external research, implementation, or test results.

## R-001: Immutable revision invalidation

**Decision:** Every manual edit or accepted suggestion appends a successor note revision using `expectedRevision`. All findings/runs bound to predecessor revisions become stale for approval but remain visible historically.

**Rationale:** Specs 001–006 consistently bind provenance and run results to immutable source/note revisions. The constitution requires material edits to invalidate earlier approval and trigger revalidation.

**Alternatives considered:** Mutating a current note row (loses provenance); copying “verified” status to successor (unsafe); visually hiding old findings (not auditable).

**Consequences:** The read model must calculate current/stale state from identity. Revision writes require transactional compare-and-append and `409 STALE_REVISION` on conflicts.

**References:** FR-19, FR-21, FR-22, FR-25; HR-004, HR-005, HR-017.

## R-002: Approval consistency and transaction scope

**Decision:** Approval eligibility and approval disposition are evaluated and inserted atomically in the review repository using the latest-revision predicate and a unique approval-per-revision constraint.

**Rationale:** A UI pre-check is insufficient: an edit may occur between checking a valid verification aggregate and persisting approval. SQLite is the constitution-approved PoC store and supports a small atomic transaction.

**Alternatives considered:** Client-side disable only (bypassable); long-lived edit locks (poor review UX and still insufficient across APIs); distributed transaction across verifiers (unnecessary and outside PoC scope).

**Consequences:** Completed upstream runs may remain historical if a concurrent edit wins. The approval service must re-check all provenance and decision predicates and return a typed conflict/precondition failure.

**References:** FR-22–FR-24; HR-008, HR-014–HR-017.

## R-003: Audit persistence is append-only logical history

**Decision:** Maintain immutable `review_decision`, `suggested_correction`, `full_note_verification`, `note_disposition`, and `audit_event` records; project current state without overwriting events.

**Rationale:** Constitution VI requires a tamper-evident or append-only logical history. Existing upstream verification and coverage runs are immutable.

**Alternatives considered:** Audit fields updated in place (loses reason/history); event sourcing all existing components (unnecessary migration/scope expansion); log-only audit (not queryable/durable enough).

**Consequences:** Audit reads need ordered event projection and reference integrity. Content duplication is minimized; existing immutable note/source records remain authoritative.

**References:** FR-25; HR-003, HR-010, HR-017.

## R-004: Finding adjudication cannot replace verification

**Decision:** Acknowledgement never resolves a finding. Dispute requires rationale. Adjudication records an accountable human decision but cannot remove a critical blocker or substitute for successful current full-note verification.

**Rationale:** The constitution makes unresolved critical contradictions and unavailable/invalid verification blocking conditions. Human authority means decisions are recorded, not that unverified evidence can be treated as valid.

**Alternatives considered:** Let any adjudication close a finding (would bypass mandatory verification); prohibit all disputes (removes reviewer feedback); use an LLM to decide appeals (violates human authority).

**Consequences:** The state model distinguishes finding resolution/adjudication from note eligibility and upstream run status. Non-critical policy resolution needs rationale and auditability.

**References:** FR-18, FR-23, FR-24; HR-003, HR-008, HR-013.

## R-005: Evidence highlighting is validation-first

**Decision:** The backend validates source/version/span and derives the excerpt before it supplies highlight metadata. The frontend displays no highlight for missing/invalid evidence and labels availability clearly.

**Rationale:** Spec 001 defines exact Unicode code-point offsets; Specs 004–006 require exact source binding and quote derivation. Browser strings use UTF-16 positions, so client conversion is a presentation concern, not evidence validation.

**Alternatives considered:** Trust model-supplied quotes/offsets (can mislead); search matching text client-side (ambiguous/repeated text); label missing evidence as contradiction (semantic error).

**Consequences:** UI needs an evidence availability state and code-point-to-UTF-16 adapter tests covering German diacritics, combining characters, emoji, and line endings. Candidate claim highlighting stays visibly separate from source evidence.

**References:** FR-17; HR-001, HR-002, HR-012.

## R-006: Full-note verification composes established owners

**Decision:** Persist a Spec 007 aggregate referencing a fresh Spec 003 claim set plus complete exact-revision runs from Specs 004, 005, and 006. It validates their binding and terminal status; it does not recreate their algorithms.

**Rationale:** User requirement and ADRs 003–005 isolate semantic verification, deterministic rules, and coverage. A single full-note eligibility assertion still needs a coherent record.

**Alternatives considered:** Re-run rules in review service (overlapping responsibility); trust any latest run without revision/source checks (stale approval); allow claim-level verification as final verification (incomplete).

**Consequences:** A missing claim-extraction façade or 005 alignment input blocks aggregate validity and must be surfaced as an external dependency, not filled from prose.

**References:** FR-21, FR-22; HR-006, HR-007, HR-014, HR-016.

## R-007: Deterministic severity policy

**Decision:** `REVIEW_SEVERITY-v1` maps upstream immutable statuses, rule codes, and recognised coverage policy keys in a documented precedence order; unknown types fail conservatively as critical.

**Rationale:** Spec 005 and ADR 005 reserve severity/approval ownership for Spec 007. The constitution prohibits model confidence as an approval authority.

**Alternatives considered:** Use an LLM severity label (non-deterministic); have each upstream component assign final severity (competing policies); leave severity absent (violates FR-15).

**Consequences:** Spec 006's free-form `severityPolicyKey` vocabulary needs a shared published mapping before implementation. Severity is a review priority, not a clinical-risk claim.

**References:** FR-15; HR-001, HR-013, HR-014.

## Unresolved design questions

| ID | Question | Required resolution / owner |
| --- | --- | --- |
| UQ-001 | What exact `severityPolicyKey` tokens will Spec 006 producers emit? | Maintainer approves a shared versioned vocabulary; review adapter retains conservative fallback. |
| UQ-002 | What component creates/retrieves complete validated source facts and explicit alignments for Spec 005 during full-note verification? | Spec 005/006 integration owner defines a reference-only adapter; no review-service matching fallback. |
| UQ-003 | Is claim extraction exposed only in-process or by a new versioned API? | Architecture owner selects injected port first or approves a public Spec 003 contract change. |
| UQ-004 | Which existing SQLite migration pattern should create review tables? | Repository maintainer confirms before persistence work; no new migration tool/dependency is assumed. |
| UQ-005 | Is a non-empty claim set required for full-note verification when extraction reports valid `EMPTY`? | Product/verification owners define the policy. Until resolved, full-note aggregate is not approval-valid. |
