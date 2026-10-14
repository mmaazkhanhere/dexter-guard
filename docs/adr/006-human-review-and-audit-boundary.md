# ADR 006: Human review, approval, and audit boundary

## Status

The implementation baseline is adopted with the explicit, time-bounded exception recorded below.
Independent requirements-quality approval remains pending and is not represented as complete by
this ADR.

## Context

Human review must compose immutable artifacts from Specs 001–006 without duplicating their
verification algorithms. Approval must remain fail-closed when revisions, evidence, or runs
become stale, while audit history must preserve every reviewer action.

## Decision

Spec 007 owns review presentation, deterministic severity mapping, finding decisions,
successor note revisions, full-note eligibility, dispositions, and append-only audit events.
Specs 001–006 retain ownership of source, note generation, claim extraction, evidence
verification, deterministic validation, and source coverage. Approval is written only inside
one repository transaction that re-checks the latest revision, exact source/run bindings,
critical findings, required decisions, and terminal full-note verification.

`REVIEW_SEVERITY-v2` classifies review priority from deterministic consequence
signals rather than treating an evidence status as severity. Medication
documentation, negation reversal, numeric mismatch, and resident-identity
signals are critical; source-verification status and any model confidence remain
independently preserved upstream metadata. Legacy v1 findings remain readable so
append-only audit history is not rewritten.

## Alternatives considered

- Let Spec 007 re-run or reimplement upstream algorithms: rejected because it creates
  competing authorities and violates contract ownership.
- Trust UI eligibility state: rejected because concurrent edits can stale the displayed result.
- Mutate a note or audit row in place: rejected because it loses provenance and rationale.

## Consequences

The design requires adapter contracts, immutable revisions, explicit stale conflicts, and
SQLite transaction tests. It adds read-model and audit persistence complexity but keeps the
PoC synchronous, local, synthetic-only, and fail-closed.

## Implementation evidence and open decision

The local boundary has regression coverage for terminal verification, stale conflicts,
idempotency replay, bounded timeout retries, content-minimized telemetry, approval guards, and
append-only audit history. It deliberately uses injected, reference-only ports: this does not
constitute approval of any production Spec 001--006 transport, timeout, retry, or error envelope.

## Explicit implementation exception (T036)

**Exception ID:** ADR-006-E1
**Owner:** Dexter Guard repository maintainers; accountable role: Spec 007 technical owner
**Scope:** The current PoC composes Specs 003–006 through injected in-process/reference-only
ports because the repository does not expose one shared production transport or atomic
cross-component transaction boundary.  This is the boundary documented in
`specs/007-human-review-and-audit/compatibility-review.md`.

**Risk:** A future production adapter could drift in source/note/claim/run identity, timeout or
retry policy, terminal-state semantics, or error-envelope details.  Treating the local doubles as
production approval would permit stale or malformed upstream evidence to affect review decisions.

**Compensating controls:**

- adapters accept immutable IDs and run metadata only; they reject source-text/claim-text
  authority and malformed results;
- review validates exact source/version, note/revision, claim-set, and component-run provenance;
- unavailable, malformed, failed, incomplete, or mismatched results are non-approval evidence;
- review approval is checked atomically in the local SQLite transaction with append-only audit
  records and idempotency constraints;
- the compatibility review and `tests/human_review` must be rerun when a production adapter is
  introduced.

**Expiry/review trigger:** 2026-12-31, or earlier when a production Spec 003–006 transport is
selected.  At expiry the owner must replace this exception with an independently reviewed
adapter contract or renew it with new evidence and risk acceptance.

This is an explicit implementation exception, not an independent reviewer approval or a claim of
overall product/release readiness.

## References

Constitution Principles I–VII; Feature 007 FR-17–FR-25; HR-004–HR-018.
