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

**Consequences:** The in-process claim-extraction port and Spec 005-owned alignment adapter are planned integration work; neither may be replaced by prose parsing or semantic matching in Spec 007.

**References:** FR-21, FR-22; HR-006, HR-007, HR-014, HR-016.

## R-007: Deterministic severity policy

**Decision:** `REVIEW_SEVERITY-v1` maps upstream immutable statuses, rule codes, and the actual Spec 006 `COVERAGE_EXPECTATION-v1` policy keys in a documented precedence order; unknown types fail conservatively as critical.

**Rationale:** Spec 005 and ADR 005 reserve severity/approval ownership for Spec 007. The constitution prohibits model confidence as an approval authority.

**Alternatives considered:** Use an LLM severity label (non-deterministic); have each upstream component assign final severity (competing policies); leave severity absent (violates FR-15).

**Consequences:** The current Spec 006 keys are mapped explicitly: `MEASUREMENT_OMISSION` to critical, and symptom/mobility/care-action/uncertainty omission keys to major. Unknown keys use the conservative fallback. Severity is a review priority, not a clinical-risk claim.

## R-008: Coverage suggestions and unresolved source items

**Decision:** A raw Spec 006 `CoverageFinding.suggestion` is display-only under CL-014. It is not a `SuggestedCorrection` and cannot be accepted directly. Spec 007 may persist a separate structured correction only after validating target note span, replacement text, and source support. Any successful coverage run with unresolved source items remains approval-blocking.

**Rationale:** Spec 006 deliberately forbids applying its suggestion and requires unresolved source items to remain review-required and never authorize approval. This preserves that ownership while allowing FR-20’s explicit-acceptance workflow.

**References:** Spec 006 CL-010, CL-014, CL-015; FR-20, FR-23; HR-011, HR-018.

**References:** FR-15; HR-001, HR-013, HR-014.

## Resolved implementation decisions

| Former question | Resolution |
| --- | --- |
| Former severity-key question | Spec 006’s current omission keys are mapped by `REVIEW_SEVERITY-v1`: `MEASUREMENT_OMISSION` to critical; symptom, mobility, care-action, and uncertainty omission keys to major; unknown/absent values use the conservative fallback. |
| UQ-002 Spec 005 inputs | A Spec 005-owned `DeterministicValidationPort.run_for_revision` resolves only existing immutable source facts and explicit alignments; Spec 007 never performs matching. |
| UQ-003 claim extraction transport | The local PoC uses an injected in-process `ClaimExtractionPort`; no public endpoint is added. |
| UQ-004 SQLite setup | The review repository uses idempotent SQLite `CREATE TABLE IF NOT EXISTS` initialization; no migration dependency is introduced. |
| UQ-005 empty claim set | A valid empty extraction result is an `INVALID` full-note aggregate (`EMPTY_CLAIM_SET_REQUIRES_REVIEW`) and blocks approval in this feature version. |

## Post-validation contract closure

The OpenAPI contract now makes the two approval-safety bindings explicit: finding-decision
commands use `expectedRevision` for compare-and-swap, and accepted suggestions require
non-null `suggestionId` and `successorRevision`. Full-note verification responses require
all three upstream run identifiers and exactly four component statuses; a `VALID` aggregate
must contain one successful status for each required component. These are contract-level
constraints; persistence and service tests remain implementation tasks.

## R-009: External contract and evaluation gates

**Decision:** Treat concrete Specs 001–006 ports/repositories and the Spec 008 benchmark
package as external dependencies until T001–T002 verify their versions and interfaces in the
implementation repository. Spec 007 will not infer missing adapters, timeout limits, retry
budgets, or evaluation thresholds.

**Rationale:** The available planning archive does not establish those implementation
artifacts. The constitution requires contract-first integration, explicit failure behavior, and
a versioned 100+ scenario benchmark before release claims.

**Alternatives considered:** Assume interfaces exist (unsafe); duplicate upstream logic
(violates ownership); reduce benchmark scope (violates the constitution).

**Consequences:** Implementation is gated on a compatibility report and Spec 008 evaluation
handoff. Missing evidence remains an explicit blocker rather than an invented interface.

**References:** Constitution IV, V, VII; T001–T002, T035; ADR 006.
