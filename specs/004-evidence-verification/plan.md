# Spec 004 — Technical Plan

**Input:** [specify.md](specify.md), [clarify.md](clarify.md), the project constitution, and [architecture.md](../../docs/architecture.md)  
**Outcome:** An evidence-linked verification service with deterministic integrity controls around structured semantic reasoning.

## Architecture alignment

This feature extends the application architecture already defined in the repository. It does not introduce a second web service, a second source of truth for transcripts, or a parallel approval workflow. Before implementation, map the module, persistence, dependency-injection, API-routing, migration, logging, and test locations in this plan to the established locations in <code>docs/architecture.md</code>; use those conventions rather than creating replacements.

The service boundary is intentionally layered:

~~~text
POST /api/v1/verification-runs
        |
        v
Request and provenance validation
        |
        v
Immutable source lookup + claim-set lookup
        |
        +--> candidate-evidence discovery (advisory only)
        |
        v
Structured semantic-verifier adapter
        |
        v
Deterministic result validation and normalization
        |
        v
Evidence span / quotation validation
        |
        v
Coverage check, immutable persistence, stable response
~~~

The candidate note enters only to establish the note revision and claim ownership. It is never passed to a component as supporting evidence for its own claims.

## Technology choices

Use the project’s existing backend runtime, web framework, persistence adapter, schema-validation library, test runner, model-client abstraction, and observability stack as specified in <code>docs/architecture.md</code>. No new runtime, database, queue, or vector store is required for the first implementation.

Within that stack, use these technology-neutral component choices:

| Concern | Choice | Rationale |
|---|---|---|
| HTTP interface | Existing versioned REST routing with schema-validated JSON | Meets the required POST interface and keeps public contracts stable. |
| Domain contracts | Strongly typed, runtime-validated schemas for request, run, finding, span, failure, and verifier response | Prevents malformed model output from entering a successful run. |
| Semantic reasoning | Existing approved LLM client behind a narrow structured-output adapter | Allows semantic German-language comparison while making model output untrusted input. |
| Evidence integrity | Deterministic Unicode code-point span utility and source-substring comparison | Makes evidence independently checkable and cross-runtime consistent. |
| Persistence | Existing relational or document persistence with append-only run records and repository abstraction | Supports provenance, auditability, and future evaluation. |
| Testing | Existing unit, contract, integration, and fixture tooling | Supports regressions without a new test platform. |
| Observability | Existing structured logs, metrics, trace/correlation IDs, and secret handling | Makes failures diagnosable without exposing unvalidated clinical text. |

If the current architecture already has a durable job mechanism for model work, submit a durable run and return its identifier. Otherwise complete a bounded short run in the request path. Both modes must persist the same <code>VerificationRun</code> contract and use the same terminal success/failure rules.

## Domain model

### Request

The request must contain:

- <code>sourceId</code> and exact <code>sourceVersion</code>;
- <code>noteId</code> and exact <code>noteRevision</code>;
- a non-empty stable claim-set identity and its atomic claims, or a reference that retrieves that exact claim set;
- per claim: stable <code>claimId</code>, assertion text, and upstream note-revision ownership; normalized semantic attributes from Spec 003 are optional but recommended;
- correlation or idempotency key if the existing API policy requires one.

Required semantic attributes, when Spec 003 provides them, include subject, predicate, value, polarity/negation, certainty/modality, attribution, temporality, and clinical-conclusion marker. They aid discovery and diagnostics but do not override the claim assertion.

### VerificationRun lifecycle

| State | Meaning | Terminal |
|---|---|---|
| RECEIVED | Parseable request accepted for processing and assigned an ID. | No |
| VALIDATING | Provenance and ownership checks are running. | No |
| VERIFYING | Candidate evidence and semantic comparison are running. | No |
| SUCCEEDED | Every claim has exactly one normalized finding with valid required grounding. | Yes |
| FAILED_VALIDATION | Source, version, note, claim, or contract validation failed. | Yes |
| FAILED_EVIDENCE_INTEGRITY | A proposed span or quotation failed deterministic validation. | Yes |
| FAILED_VERIFIER | Timeout, unavailable provider, or malformed/invalid structured model response. | Yes |
| FAILED_PERSISTENCE | Run outcome could not be made durably traceable. | Yes |

Only <code>SUCCEEDED</code> may include authoritative <code>findings</code>. A terminal failure includes a machine-readable failure code, a safe human-readable reason, model/prompt identity when available, and correlation ID. It must not convert errors into <code>UNCERTAIN</code> or any other evidence status.

### Evidence contracts

#### EvidenceStatus

Exactly one of <code>SUPPORTED</code>, <code>UNSUPPORTED</code>, <code>CONTRADICTED</code>, or <code>UNCERTAIN</code>.

#### SourceSpan

~~~text
sourceId: stable identifier, equal to VerificationRun.sourceId
sourceVersion: immutable version, equal to VerificationRun.sourceVersion
startOffset: non-negative Unicode code-point offset, inclusive
endOffset: Unicode code-point offset, exclusive and greater than startOffset
text: exact substring derived from immutable source between offsets
~~~

The source text is held exactly as versioned by Spec 001. Display normalization, line-ending normalization, token offsets, byte offsets, and UTF-16 offsets are not valid substitutes for contract offsets.

#### EvidenceFinding

~~~text
claimId: input claim identifier
status: one EvidenceStatus
explanation: concise reviewer-facing basis
sourceSpans: validated spans; required except for UNSUPPORTED
discrepancies: zero or more typed semantic changes
policyVersion: CERTAINTY-v1 for certainty-governed outcome
~~~

Discrepancy types are <code>NEGATION</code>, <code>CERTAINTY</code>, <code>ATTRIBUTION</code>, <code>CLINICAL_INFERENCE</code>, and <code>OTHER</code>. They enrich the primary status; they never replace it.

#### VerificationRun

Persist run ID, input identity/digest, source ID/version, note ID/revision, status, findings or failure, verifier model and version, prompt version/hash, annotation-policy version, created/started/completed timestamps, correlation ID, and idempotency linkage where available.

## Verification algorithm

1. **Parse and validate request shape.** Reject missing required fields, duplicate claim IDs, empty claim sets, invalid claim text, and invalid identity formats before semantic processing.
2. **Validate provenance.** Resolve immutable source snapshot, candidate note revision, and claim set. Confirm each claim exists exactly once and belongs to requested note revision. Reject source/version mismatch and stale or cross-note claim references.
3. **Prepare source representation.** Preserve exact source string and build a Unicode code-point index utility. Do not modify source text or use a normalized derivative for evidence offsets.
4. **Discover candidate evidence.** Use claim text and normalized attributes to select useful passages. For short transcripts, present the whole source. Discovery scores are advisory and never decide evidence status.
5. **Perform semantic comparison.** Call structured verifier with claim, only immutable source evidence, candidate passages or full source, status definitions, qualifier rules, and CERTAINTY-v1. Require one candidate result per claim, valid enum status, concise explanation, discrepancy types, and proposed spans.
6. **Validate structured response.** Reject malformed JSON, invalid enums, duplicate/missing/foreign claim IDs, excess findings, missing required reason, unsupported fields that affect meaning, and timeout/provider errors.
7. **Validate evidence references.** For every proposed span, verify source ID/version equality, integer boundaries, non-empty range, offset range, and exact source-derived quotation. Reject any mismatch. For statuses that require grounding, reject empty spans.
8. **Normalize classification.** Deterministically enforce status precedence and policy constraints; ensure unsupported has no claimed support and qualifier discrepancies are required when detected. Do not override invalid semantic response with a guessed status.
9. **Check coverage.** Require one normalized finding for every submitted claim and no extra findings.
10. **Persist and return.** Atomically persist immutable run and return stable response. A persistence failure is non-successful and must never be represented as verified.

## Structured verifier boundary

The semantic adapter owns prompt construction, provider invocation, retry policy, timeout, and schema parsing. It receives no authority to persist findings, approve notes, or alter inputs. Its response is treated like untrusted external input.

The adapter must require:

- output in the declared schema only, with no free-form reasoning required for downstream parsing;
- one candidate result per input claim;
- a primary status from the allowed enum;
- bounded reviewer-facing explanation;
- source spans with offsets under the published contract;
- discrepancy types and certainty-policy application where applicable.

Timeouts and malformed output are terminal verifier failures after only the safe retry policy already authorized by the architecture. Retrying cannot reuse candidate-note text as evidence or change source version.

## Persistence and integrity

Use immutable run records. The parent record stores provenance and lifecycle metadata; child finding/span records or embedded immutable equivalents preserve order and all required fields. Enforce database-level or transactional uniqueness for:

- run identifier;
- one finding per <code>(verificationRunId, claimId)</code>;
- one immutable source identity per run;
- input idempotency association if supported by the existing platform.

Persist a source-content digest when available from Spec 001. It supplements, but never replaces, required source ID/version lookup. Store prompt and annotation-policy versions, not hidden prompt reasoning.

## API design

### POST /api/v1/verification-runs

The endpoint creates one verification attempt. Its response schema always includes run ID, lifecycle status, source and note identity, and either:

- <code>findings</code> for a successful terminal run; or
- <code>failure</code> for a terminal failure.

Malformed HTTP payloads that cannot form an identifiable run may use the application’s standard client-validation response. Once a request has enough identity to create a run, source mismatch, stale ownership, verifier timeout, and evidence-integrity failure must be represented durably as a non-successful run. The endpoint must never return a success envelope containing partial or unvalidated findings.

Authorization, authentication, rate limits, and error-envelope shape follow the existing API architecture. The endpoint must not expose transcript text beyond evidence spans needed by an authorized reviewer.

## Test strategy

| Level | Focus |
|---|---|
| Unit | Unicode code-point offset conversion, span boundary/quotation integrity, status precedence, CERTAINTY-v1, negation scope, attribution, all-or-nothing coverage, and failure normalization. |
| Contract | Request and response schemas, enum closure, mandatory provenance, success/failure exclusivity, stable error envelope, and unknown-field behavior. |
| Integration | Immutable source and claim lookup, persistence transaction, API lifecycle, model adapter with deterministic stub, cross-note rejection, and authorization integration. |
| Regression | EV-001 through EV-014 with German fixtures, including equivalent terminology and compound partial-negation cases. |
| Evaluation handoff | Emit fixtures and labeled expected findings consumable by Spec 008; report classification errors and false positives there, not in production request flow. |

## Security, privacy, and operations

- Follow the constitution and architecture requirements for protected health information, access control, retention, audit logging, model-provider approval, and secrets.
- Do not log full transcripts, raw prompts, or model outputs at ordinary log levels. Log IDs, digests, status, error codes, timings, and approved redacted diagnostics.
- Record model, prompt, and policy versions for reproducibility.
- Track run success/failure counts, model latency/timeouts, span-integrity failures, coverage failures, and status distribution.
- Approval remains outside this spec. Consumers must treat any status other than successful verification as not approved.

## Implementation readiness

The plan is ready once its repository location mapping has been checked against the architecture document. It deliberately leaves no product-policy ambiguity: semantic model choice can vary, but the deterministic contracts and safe terminal behavior cannot.
