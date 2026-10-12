# ADR 003: Evidence-verification execution and provenance boundary

## Status

Accepted for the synthetic Spec 004 proof of concept.

## Context

Spec 004 verifies immutable, extracted nursing-note claims against one
immutable German source version. It must preserve the source-first architecture
and make retries safe without introducing a second source of truth, background
job API, resident-inference workflow, or untraceable model output.

The relevant upstream contracts already establish immutable source versions
(Spec 001), note revisions (Spec 002), and extraction results with claims
(Spec 003). The verification boundary needs a durable execution model,
unambiguous claim ownership, and a safe retry rule for model-backed work.

## Decision

- Expose Spec 004 as a bounded synchronous `POST /api/v1/verification-runs`
  operation. It returns a terminal durable run under HTTP 200, whether the run
  succeeds or fails. It does not expose HTTP 202, polling, callbacks, or a
  background-job contract.
- Consume immutable upstream references only. The requested `(sourceId,
  sourceVersion)` resolves through Spec 001; `(noteId, noteRevision)` resolves
  through Spec 002; and `claimSetId` is exactly the immutable Spec 003
  `extractionRunId`. Claim IDs are resolved from that extraction result rather
  than accepting client-provided assertion text.
- Require the one synthetic `residentTestId` on every claim reference to match
  the immutable source and resolved claim record. Reject unknown or mismatched
  identities; do not infer or disambiguate residents.
- Bind each idempotency key atomically to a canonical digest of source identity,
  note identity, claim-set identity, and claim references. The same key and
  digest return the existing run; the same key with a different digest returns
  HTTP 409 `IDEMPOTENCY_KEY_CONFLICT` before model invocation or a new run is
  persisted.
- Treat semantic-verifier output as untrusted structured input. Deterministic
  controls own provenance, coverage, source-span, quotation, and persistence
  validation; they do not replace the verifier's semantic judgment.
- Persist append-only verification runs through the existing repository
  architecture, using SQLite for the local PoC. In-memory stores are test
  doubles only.

## Consequences

The public API has predictable terminal semantics and callers can safely retry
without receiving a run produced for another request. Exact source, note, and
claim provenance are preserved across components, and no new resident identity
or transcript authority is introduced.

The request path is limited by the bounded verifier timeout; a timeout is a
terminal `FAILED_VERIFIER` outcome rather than an asynchronous pending state.
If asynchronous verification is needed later, it requires a separate ADR and a
separately versioned API contract defining submission, job status, retrieval or
callback delivery, idempotency, and terminal-failure behavior.
