# Spec 004 — Requirements Quality Checklist

**Reviewer-owned artifact:** This checklist assesses whether the specification is clear, complete, internally consistent, and testable. It does not track implementation progress. A reviewer, not the implementation workflow, checks an item only after verifying the criterion.

**Review state:** Contract requirements reviewed on 2026-10-12. Integration-test criteria remain open pending implementation of the verification service, repositories, and API. Corrections are recorded in [compatibility-review.md](compatibility-review.md), including the immutable claim-set mapping and idempotency conflict semantics.

## Requirement clarity

- [x] Every requirement uses unambiguous normative language and identifies the responsible system behavior.
- [x] The four evidence statuses are mutually exclusive and collectively exhaustive for successfully verified claims.
- [x] The distinction between UNSUPPORTED and CONTRADICTED is explicit and has at least one negative example.
- [x] The definition of UNCERTAIN distinguishes unresolved relevant evidence from verifier or infrastructure failure.
- [x] “Evidence,” “claim,” “source version,” “note revision,” and “successful run” have one consistent meaning throughout the documents.
- [x] Character span indexing is defined precisely enough to implement independently across supported runtime languages.
- [x] The partial-negation example defines scope behavior rather than relying on a keyword heuristic.
- [x] Certainty behavior has a versioned policy and clearly states when it is uncertain versus contradicted.
- [x] Attribution behavior distinguishes patient report, third-party report, and confirmed clinical observation.

## Completeness

- [x] FR-07, FR-08, FR-09, FR-10, FR-12, and FR-13 each map to explicit specification requirements and test coverage.
- [x] The source transcript is unambiguously the sole evidence authority and the note cannot self-support its own claims.
- [x] Every input provenance relation is specified: source ID/version, note ID/revision, claim ID/set, and claim ownership.
- [x] The data contracts fully specify EvidenceStatus, SourceSpan, EvidenceFinding, and VerificationRun.
- [x] A successful run requires exactly one finding for every submitted valid claim and no additional claims.
- [x] Required evidence spans and the lone exception for unsupported findings are specified.
- [x] Failure paths cover malformed requests, stale source versions, invalid offsets, quotation mismatch, duplicate/missing findings, malformed model output, timeout, and persistence failure.
- [x] Safe failure explicitly prevents note approval and authoritative partial findings.
- [x] API behavior distinguishes syntactically invalid requests from identifiable verification attempts that fail during processing.
- [x] Privacy, auditability, version traceability, and observability requirements are present.
- [x] Ownership boundaries with Specs 001–003 and 005–008 prevent duplicate or missing responsibility.

## Consistency

- [x] Status precedence in the specification, clarification record, plan, and tests is identical.
- [x] Source-span rules in the specification and plan use the same zero-based, inclusive/exclusive Unicode code-point convention.
- [x] Plan lifecycle permits findings only for successful runs, matching the specification.
- [x] Tasks do not assign numerical/unit validation, completeness analysis, approval decisions, or source mutation to Spec 004.
- [x] Model behavior is consistently treated as untrusted structured input, with deterministic integrity checks before success.
- [x] No requirement requires both a primary evidence status and a failure status for the same claim/run outcome.
- [x] Acceptance scenarios, test tasks, and contract requirements use the same claim IDs and expected result vocabulary.

## Testability

- [x] Each acceptance scenario has a deterministic fixture design, expected primary status, expected claim identifier, and expected evidence/discrepancy assertion.
- [x] Regression cases cover equivalent German terminology without allowing qualifier loss.
- [x] Regression cases cover negation reversal and partial negation separately.
- [x] Regression cases cover both ordinary uncertainty and explicitly unconfirmable certainty claims.
- [x] Regression cases cover attribution escalation and unsupported clinical diagnosis.
- [x] Integrity tests prove quotations are derived from validated offsets rather than model-provided strings.
- [x] Contract tests reject unknown evidence statuses and illegal source-span values.
- [ ] Integration tests prove a stale source version and cross-note claim are non-successful.
- [ ] Failure tests demonstrate that malformed verifier output and timeout cannot return an authoritative result.
- [x] Evaluation-handoff requirements permit Spec 008 to measure errors and false positives from stable labeled fixtures.

## Review decision

- [ ] The reviewer finds the specification ready for implementation planning.
- [x] The reviewer records the open integration-test follow-up and required compatibility corrections in the issue/review artifacts.
