# Spec 004 evidence-verification operations

This runbook covers the synchronous synthetic-demo verifier at
`POST /api/v1/verification-runs`. It does not configure a production model,
approval workflow, or the held-out evaluation owned by Spec 008.

## Configuration boundary

`VerificationService` receives its dependencies through constructor injection.
The approved provider must be wrapped by `StructuredVerifierAdapter` and expose
model/prompt identity metadata. The service defaults are:

| Setting | Default | Safety rule |
|---|---:|---|
| Provider timeout | 30 seconds | A timeout returns `FAILED_VERIFIER/PROVIDER_TIMEOUT`. |
| Maximum provider attempts | 2 | Retries reuse the same run identifier and never change the request digest. |
| Persistence | In-memory demo repository | Production deployments must provide the existing repository boundary; no upstream record is mutated. |
| Prompt | `verification-v1` | The prompt hash is retained on every terminal run. |
| Annotation policy | `EVIDENCE_ANNOTATION-v1` | Unknown policy versions fail closed. |

The verifier receives only the resolved immutable claim material and exact
source transcript required for the run. The request cannot supply assertion
text, source text, or a resident inference.

## Terminal outcomes

- `SUCCEEDED`: every submitted claim has exactly one validated finding.
- `FAILED_VALIDATION`: source, note, claim-set, resident, or provenance lookup failed.
- `FAILED_EVIDENCE_INTEGRITY`: a span, quotation, status/evidence pairing, or coverage rule failed.
- `FAILED_VERIFIER`: provider timeout, unavailability, or malformed/unsupported structured output.
- `FAILED_PERSISTENCE`: the complete result could not be durably saved.

Only `SUCCEEDED` contains authoritative findings. `UNCERTAIN` is a semantic
finding, not a provider or infrastructure failure.

## Troubleshooting

1. Check `failure.code`, `correlationId`, `executionTraceId`, model/prompt
   identity, and policy versions. Do not log transcript text, prompts, claims,
   or raw provider output.
2. For `SOURCE_NOT_FOUND`, `SOURCE_VERSION_MISMATCH`, `CLAIM_REVISION_MISMATCH`,
   or `RESIDENT_MISMATCH`, resolve the immutable upstream identifiers; never
   substitute a newer source or reconstruct a claim reference.
3. For `INVALID_EVIDENCE`, inspect provider span coordinates against the exact
   source version. Quotes must be derived from the validated code-point range.
4. For `MALFORMED_VERIFIER_OUTPUT`, validate the provider’s structured schema,
   policy version, unique claim coverage, and required explanation before retry.
5. For `PROVIDER_TIMEOUT` or `PROVIDER_UNAVAILABLE`, retry the same idempotency
   key only after provider health is restored. A retry cannot turn a failure
   into an evidence status without a complete new verification result.

## Retention and privacy

Verification runs are append-only and retain provenance, policy/model/prompt
versions, timestamps, correlation identifiers, and safe failure codes. The
service telemetry is content-free. Transcript text, prompts, raw model output,
and claim text must remain outside logs and metrics; retention of persisted
source and run records follows the repository’s synthetic-data policy.

