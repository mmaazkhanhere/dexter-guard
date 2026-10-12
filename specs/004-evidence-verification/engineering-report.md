# Spec 004 engineering report

## Delivered

The feature branch `spec-04/evidence-verification` adds strict Pydantic run,
failure, finding, span, quotation, discrepancy, and verifier-response contracts;
an injected `VerificationService`; pluggable structured verifier adapters with
bounded retries and timeout handling; immutable source/claim/note provenance
checks; Unicode code-point span and source-derived quotation validation;
all-or-nothing findings; in-memory and SQLite run persistence with atomic
idempotency replay/conflict handling; the synchronous
`POST /api/v1/verification-runs` route; redacted telemetry; and a versioned
`verification_v1` prompt asset.

The convergence follow-up adds an exact Unicode source-text index, versioned
EV-001 through EV-014 German fixtures and critical-case manifest, immutable
source/note/claim API acceptance coverage, content-free lifecycle telemetry,
an operations runbook, and a versioned development-evaluation handoff for
Spec 008.

Semantic labels remain provider-owned. Deterministic code validates contract,
coverage, provenance, source identity, offsets, quotations, and persistence; it
does not infer clinical meaning. Execution failures remain `FAILED_*` outcomes
and never become `UNCERTAIN` or `UNSUPPORTED`.

## Requirement traceability

FR-07 is covered by immutable claim-set resolution and exact finding coverage.
FR-08 is covered by `SourceSpan`, Unicode boundary checks, and derived quotes.
FR-09 and FR-10 are represented as distinct provider statuses with safe failure
handling. FR-12 is covered by discrepancy labels and German negation, certainty,
and attribution cases. FR-13 is covered by unsupported clinical-inference cases.
The API and persistence metadata retain source/note/claim identities, policy
versions, model/prompt identity, input digest, timestamps, correlation ID, and
execution trace ID.

## Verification performed

- `uv run pytest -q`: 130 passed before the convergence follow-up; the full suite is rerun for T029.
- `uv run pytest tests/evidence_verification -q`: 62 passed after the convergence follow-up.
- `uv run python -m compileall -q src tests`: passed.
- `git diff --check`: passed.

The tests include malformed/unknown/duplicate verifier findings, timeout and
provider failure paths, stale source versions, stale/cross-note claims, resident
mismatch, quotation mismatch, invalid spans, unsupported-without-evidence,
idempotent replay, HTTP 400/409 behavior, and German qualifier regressions.

## Known limitations and remaining risks

- A production LLM SDK/provider is not configured in this synthetic PoC; the
  development report therefore uses a deterministic configured fixture verifier
  behind the same structured adapter. A real provider run must produce a new
  report before external deployment.
- Candidate-evidence discovery is intentionally not a separate retrieval
  subsystem; short transcripts are supplied in full and provider output remains
  advisory input.
- The operations runbook and evaluation handoff explicitly keep persistence,
  raw-text redaction, and held-out benchmark ownership outside this service.
- The reviewer-owned Spec Kit checklist still requires an independent reviewer
  to close its integration-test markers. The implementation task record preserves
  that approval boundary rather than self-approving it. Spec 008 still owns
  held-out evaluation thresholds and release reporting.
- Numeric/unit validation, completeness/omission analysis, approval decisions,
  and audit workflows remain outside Spec 004 as required.
