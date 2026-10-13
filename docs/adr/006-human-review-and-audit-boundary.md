# ADR 006: Human review, approval, and audit boundary

## Status

Implementation evidence is recorded, but independent approval remains pending. Compatibility
verification is recorded in `specs/007-human-review-and-audit/compatibility-review.md`; an
independent reviewer must either approve this ADR or document an exception with an owner, risk,
compensating control, and expiry before the status can become Accepted.

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
constitute approval of any production Spec 001--006 transport, timeout, retry, or error
envelope. The remaining reviewer decision is therefore a governance gate, not an inferred
technical sign-off.

## References

Constitution Principles I–VII; Feature 007 FR-17–FR-25; HR-004–HR-018.
