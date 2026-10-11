# Spec 004 — Requirements Quality Checklist

**Reviewer-owned artifact:** This checklist assesses whether the specification is clear, complete, internally consistent, and testable. It does not track implementation progress. A reviewer, not the implementation workflow, checks an item only after verifying the criterion.

**Review state:** Pending independent review. All items intentionally remain unchecked.

## Requirement clarity

- [ ] Every requirement uses unambiguous normative language and identifies the responsible system behavior.
- [ ] The four evidence statuses are mutually exclusive and collectively exhaustive for successfully verified claims.
- [ ] The distinction between UNSUPPORTED and CONTRADICTED is explicit and has at least one negative example.
- [ ] The definition of UNCERTAIN distinguishes unresolved relevant evidence from verifier or infrastructure failure.
- [ ] “Evidence,” “claim,” “source version,” “note revision,” and “successful run” have one consistent meaning throughout the documents.
- [ ] Character span indexing is defined precisely enough to implement independently across supported runtime languages.
- [ ] The partial-negation example defines scope behavior rather than relying on a keyword heuristic.
- [ ] Certainty behavior has a versioned policy and clearly states when it is uncertain versus contradicted.
- [ ] Attribution behavior distinguishes patient report, third-party report, and confirmed clinical observation.

## Completeness

- [ ] FR-07, FR-08, FR-09, FR-10, FR-12, and FR-13 each map to explicit specification requirements and test coverage.
- [ ] The source transcript is unambiguously the sole evidence authority and the note cannot self-support its own claims.
- [ ] Every input provenance relation is specified: source ID/version, note ID/revision, claim ID/set, and claim ownership.
- [ ] The data contracts fully specify EvidenceStatus, SourceSpan, EvidenceFinding, and VerificationRun.
- [ ] A successful run requires exactly one finding for every submitted valid claim and no additional claims.
- [ ] Required evidence spans and the lone exception for unsupported findings are specified.
- [ ] Failure paths cover malformed requests, stale source versions, invalid offsets, quotation mismatch, duplicate/missing findings, malformed model output, timeout, and persistence failure.
- [ ] Safe failure explicitly prevents note approval and authoritative partial findings.
- [ ] API behavior distinguishes syntactically invalid requests from identifiable verification attempts that fail during processing.
- [ ] Privacy, auditability, version traceability, and observability requirements are present.
- [ ] Ownership boundaries with Specs 001–003 and 005–008 prevent duplicate or missing responsibility.

## Consistency

- [ ] Status precedence in the specification, clarification record, plan, and tests is identical.
- [ ] Source-span rules in the specification and plan use the same zero-based, inclusive/exclusive Unicode code-point convention.
- [ ] Plan lifecycle permits findings only for successful runs, matching the specification.
- [ ] Tasks do not assign numerical/unit validation, completeness analysis, approval decisions, or source mutation to Spec 004.
- [ ] Model behavior is consistently treated as untrusted structured input, with deterministic integrity checks before success.
- [ ] No requirement requires both a primary evidence status and a failure status for the same claim/run outcome.
- [ ] Acceptance scenarios, test tasks, and contract requirements use the same claim IDs and expected result vocabulary.

## Testability

- [ ] Each acceptance scenario has a deterministic fixture design, expected primary status, expected claim identifier, and expected evidence/discrepancy assertion.
- [ ] Regression cases cover equivalent German terminology without allowing qualifier loss.
- [ ] Regression cases cover negation reversal and partial negation separately.
- [ ] Regression cases cover both ordinary uncertainty and explicitly unconfirmable certainty claims.
- [ ] Regression cases cover attribution escalation and unsupported clinical diagnosis.
- [ ] Integrity tests prove quotations are derived from validated offsets rather than model-provided strings.
- [ ] Contract tests reject unknown evidence statuses and illegal source-span values.
- [ ] Integration tests prove a stale source version and cross-note claim are non-successful.
- [ ] Failure tests demonstrate that malformed verifier output and timeout cannot return an authoritative result.
- [ ] Evaluation-handoff requirements permit Spec 008 to measure errors and false positives from stable labeled fixtures.

## Review decision

- [ ] The reviewer finds the specification ready for implementation planning.
- [ ] The reviewer records any required follow-up in the issue or review system without modifying these reviewer-owned marks automatically.
