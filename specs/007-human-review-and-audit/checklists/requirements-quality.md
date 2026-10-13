# Spec 007 Requirements Quality Checklist

**Reviewer-owned gate:** An independent reviewer must approve the checked items before
implementation. The architecture self-review recorded below found no documentation defect,
but it does not substitute for reviewer sign-off or implementation evidence. Checked items
represent requirements-quality review, not implementation completion.

**Independent reviewer approval:** **NOT APPROVED -- exceptions recorded.** The formal
review record below replaces the prior pending state. No dependent work, release, or production
integration may treat this checklist as approved until every listed exception is remediated and
independently re-reviewed.

## Independent review record

- **Reviewer:** Codex (automated repository reviewer)
- **Review date:** 2026-10-13
- **Reviewed baseline:** working tree at the start of this review; implementation evidence in
  `src/human_review`, `tests/human_review`, Specs 001--007, ADR 006, and the published OpenAPI
  contracts.
- **Decision:** **NOT APPROVED -- two blocking evidence-integrity/approval-safety exceptions.**
  This is a requirements-quality and implementation-conformance review, not a clinical,
  production-readiness, or release approval.

### Confirmed items

- The Spec 001--006 ownership and integration boundaries are correctly stated: Spec 007 consumes
  immutable references and terminal metadata through reference-only ports; it does not take over
  source ingestion, note generation, claim extraction, evidence classification, deterministic
  validation, or coverage assessment. ADR-006-E1 remains a valid, time-bounded PoC exception
  for the absent production aggregate transport and expires on 2026-12-31.
- The reviewed specification, data model, contracts, task traceability, and HR-001--HR-018
  scenarios are mutually traceable. The scope exclusions are preserved in the inspected code and
  task inventory: no clinical decisioning, real data, auth/RBAC, EHR integration, mobile,
  queues/microservices, or model training was added.
- Executed evidence: `.venv\\Scripts\\python.exe -m pytest -q` (313 passed),
  `.venv\\Scripts\\python.exe -m pytest -q tests\\human_review` (61 passed),
  `.venv\\Scripts\\python.exe -m compileall -q src tests`, and `git diff --check` all passed.
  The existing Starlette/httpx deprecation warning is non-blocking.

### Blocking exceptions

- **IR-007-01 -- Severity policy is implemented and tested contrary to the written fail-safe
  contract.** `spec.md` defines Spec 004 `UNSUPPORTED` and `UNCERTAIN` as `MAJOR`, Spec 005
  `NOT_EVALUABLE` as `MAJOR`, and unknown upstream finding types as `CRITICAL` until a policy
  revision. `src/human_review/policy.py` instead returns `MINOR` for `UNSUPPORTED` and for
  unknown inputs; `tests/human_review/test_policy.py` asserts those unsafe results. This violates
  CQ-006, CQ-007, CQ-016, FR-15, and the approval-blocking safety model. Update the mapper and
  tests to the documented closure, including explicit coverage for `UNCERTAIN`,
  `NOT_EVALUABLE`, and unknown producer types, then rerun approval and acceptance tests.
- **IR-007-02 -- The claim-feedback and structured-correction paths do not yet prove the required
  source/provenance integrity.** `ReviewService.record_claim_feedback` accepts only an opaque
  upstream run ID and persists no claim-set/run source or revision validation. `add_suggestion`
  checks only source ID/version on support spans; it does not resolve the span against the
  immutable source text or verify an exact source-derived quotation before allowing a `USABLE`
  correction. This falls short of FR-20/FR-21, CQ-011, CQ-014, CQ-015, and the stated
  no-invented-facts rule. Add typed reference-only metadata validation for claim feedback and a
  Spec 001-backed span/quote validation step for usable corrections, with failing/successful
  provenance tests.

**Re-approval condition:** Close IR-007-01 and IR-007-02 with implementation, contract and
acceptance-test evidence; update this record with the new reviewer, date, reviewed revision, and
an explicit approval decision. Passing the current suite alone is not evidence of closure because
it presently asserts part of IR-007-01.

**Architecture self-review:** PASS for CQ-001–CQ-024 on 2026-10-12. Upstream implementation
compatibility remains an explicit external dependency documented in
`compatibility-review.md`; T001–T002 must complete that verification before implementation.

**Requirements validation:** PASS for CQ-001–CQ-024 on 2026-10-12. The checklist was
validated against the Spec 007 specification, plan, tasks, data model, contracts,
clarifications, research, consistency analysis, compatibility review, and ADR 006.

## Completeness

- [x] CQ-001 Feature goal, PoC scope, non-goals, and ownership boundaries with Specs 001–006 are explicit.
- [x] CQ-002 FR-15 and FR-17–FR-25 each map to acceptance scenarios, contracts, tasks, and completion evidence.
- [x] CQ-003 The distinction between note status, finding status, and upstream verification-run status is unambiguous.
- [x] CQ-004 Full-note verification names all required component results and exact source/note/claim-set bindings.
- [x] CQ-005 Audit history covers original candidate, revisions, findings/runs, suggestions, decisions, and dispositions with attribution/timing.

## Clarity and consistency

- [x] CQ-006 Severity policy is deterministic, reviewable, and does not use an LLM label as authority.
- [x] CQ-007 `UNSUPPORTED`, missing evidence, invalid evidence, and direct contradiction have distinct display and approval semantics.
- [x] CQ-008 Acknowledgement, dispute, adjudication, resolution, and staleness rules are explicit; acknowledgement cannot clear critical discrepancy.
- [x] CQ-009 Revision identifiers, expected-revision conflict behavior, and stale approval handling are consistent across spec, model, plan, and contract.
- [x] CQ-010 The proposed OpenAPI schemas use a compatible `{code,message}` error envelope and do not assert that unimplemented endpoints exist.

## Evidence integrity and safety

- [x] CQ-011 Source spans use the exact immutable Spec 001 source version and documented Unicode offset semantics.
- [x] CQ-012 Candidate-note spans are never represented as evidence for themselves.
- [x] CQ-013 Missing/invalid spans cannot create misleading highlights or authorize approval.
- [x] CQ-014 Unsupported suggestions cannot introduce facts or be accepted.
- [x] CQ-015 Edits invalidate predecessor verification eligibility; claim-level feedback cannot replace final full-note verification.
- [x] CQ-016 Failed, malformed, incomplete, or source-mismatched verification cannot authorize approval; rejection remains available.
- [x] CQ-017 Approval guard is backend-enforced and atomic against a concurrent revision change.

## Scope and implementation readiness

- [x] CQ-018 No diagnosis, treatment, real data, auth/RBAC, EHR integration, mobile, queues, microservices, or model training requirement was added.
- [x] CQ-019 Missing Spec 003 facade, Spec 005 alignment, Spec 006 severity-key vocabulary, and migration dependencies are explicit rather than assumed.
- [x] CQ-020 Tasks are dependency ordered, use standard checkboxes/parallel markers, and include contract, state, UI, integration, acceptance, and regression tests.
- [x] CQ-021 All required acceptance scenarios use synthetic German nursing documentation only.

## Constitution and dependency closure

- [x] CQ-022 The Spec 008 benchmark handoff is explicit; Spec 007 does not claim the required
  100+ scenario evaluation or release thresholds have already run.
- [x] CQ-023 Concrete Specs 001–006 implementations, versions, timeout/retry behavior, and
  migrations are treated as external dependencies until T001–T002 verify them in the target
  repository.
- [x] CQ-024 Cross-component review, approval, and audit ownership is recorded in ADR 006.
