# Spec 007 Requirements Quality Checklist

**Reviewer-owned gate:** Mark an item `[x]` only after an independent reviewer establishes the stated condition. This planning change does not mark any item complete. Checked items represent requirements-quality review, not implementation completion.

## Completeness

- [ ] CQ-001 Feature goal, PoC scope, non-goals, and ownership boundaries with Specs 001–006 are explicit.
- [ ] CQ-002 FR-15 and FR-17–FR-25 each map to acceptance scenarios, contracts, tasks, and completion evidence.
- [ ] CQ-003 The distinction between note status, finding status, and upstream verification-run status is unambiguous.
- [ ] CQ-004 Full-note verification names all required component results and exact source/note/claim-set bindings.
- [ ] CQ-005 Audit history covers original candidate, revisions, findings/runs, suggestions, decisions, and dispositions with attribution/timing.

## Clarity and consistency

- [ ] CQ-006 Severity policy is deterministic, reviewable, and does not use an LLM label as authority.
- [ ] CQ-007 `UNSUPPORTED`, missing evidence, invalid evidence, and direct contradiction have distinct display and approval semantics.
- [ ] CQ-008 Acknowledgement, dispute, adjudication, resolution, and staleness rules are explicit; acknowledgement cannot clear critical discrepancy.
- [ ] CQ-009 Revision identifiers, expected-revision conflict behavior, and stale approval handling are consistent across spec, model, plan, and contract.
- [ ] CQ-010 The proposed OpenAPI schemas use a compatible `{code,message}` error envelope and do not assert that unimplemented endpoints exist.

## Evidence integrity and safety

- [ ] CQ-011 Source spans use the exact immutable Spec 001 source version and documented Unicode offset semantics.
- [ ] CQ-012 Candidate-note spans are never represented as evidence for themselves.
- [ ] CQ-013 Missing/invalid spans cannot create misleading highlights or authorize approval.
- [ ] CQ-014 Unsupported suggestions cannot introduce facts or be accepted.
- [ ] CQ-015 Edits invalidate predecessor verification eligibility; claim-level feedback cannot replace final full-note verification.
- [ ] CQ-016 Failed, malformed, incomplete, or source-mismatched verification cannot authorize approval; rejection remains available.
- [ ] CQ-017 Approval guard is backend-enforced and atomic against a concurrent revision change.

## Scope and implementation readiness

- [ ] CQ-018 No diagnosis, treatment, real data, auth/RBAC, EHR integration, mobile, queues, microservices, or model training requirement was added.
- [ ] CQ-019 Missing Spec 003 facade, Spec 005 alignment, Spec 006 severity-key vocabulary, and migration dependencies are explicit rather than assumed.
- [ ] CQ-020 Tasks are dependency ordered, use standard checkboxes/parallel markers, and include contract, state, UI, integration, acceptance, and regression tests.
- [ ] CQ-021 All required acceptance scenarios use synthetic German nursing documentation only.
