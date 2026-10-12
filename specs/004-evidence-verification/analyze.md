# Spec 004 — Consistency Analysis

**Analysis type:** Read-only cross-artifact review  
**Artifacts reviewed:** spec.md, clarify.md, annotation-policy.md, plan.md, tasks.md, contracts, and Specs 001–003 interfaces
**Result:** No unresolved policy conflicts remain. The synchronous PoC contract is fixed, but implementation readiness remains blocked by the outstanding integration-test checklist items and repository/API wiring.

## Requirement traceability

| Requirement | Specification coverage | Planned control | Task coverage |
|---|---|---|---|
| FR-07, verify every claim | US-1; functional requirements; definition of done | provenance validation, semantic comparison, coverage check | T010, T016, T020, T021, T025 |
| FR-08, source character spans | US-2; SourceSpan contract | Unicode code-point validator and derived quotation | T006–T009, T016, T024 |
| FR-09, unsupported | status policy; EV-002 and EV-014 | precedence and no-span exception | T016, T017, T024 |
| FR-10, contradiction | status policy; EV-003 and EV-004 | explicit-conflict precedence | T016, T017, T024 |
| FR-12, negation/certainty/attribution | qualifier policy; EV-004–EV-006, EV-013 | discrepancy model and EVIDENCE_ANNOTATION-v1 | T016, T017, T024 |
| FR-13, unsupported clinical conclusion | qualifier policy; EV-007 | clinical-inference discrepancy | T016, T017, T024 |

## Consistency checks

| Check | Result | Evidence |
|---|---|---|
| Exactly one status per successfully verified claim | Pass | spec.md requires one primary status; plan.md coverage check; T016 and T021 enforce it. |
| Failure distinct from evidence status | Pass | clarify CL-003/CL-013, plan lifecycle, and T019 restrict findings to SUCCEEDED runs. |
| Source is sole evidence authority | Pass | specify scope and plan architecture prohibit candidate-note self-support; T012 constrains the semantic port. |
| Offsets and quotations independently checkable | Pass | clarify CL-004/CL-005 and plan SourceSpan contract agree; T006–T009 test them. |
| Unsupported distinct from contradicted | Pass | same precedence appears in spec, clarification, plan, and regression tasks. |
| Certainty ambiguity does not become an unexplained contradiction | Pass | EVIDENCE_ANNOTATION-v1 documented in clarify CL-007 and consumed by plan/T016/T017. |
| Partial negation cannot be reduced to negative-token match | Pass | explicit in spec, clarification, test strategy, T017, and EV-013. |
| Spec boundaries retained | Pass | numeric/unit work, omissions, approval, and benchmark ownership stay with Specs 005–008 in all artifacts. |
| API supports safe failure | Pass | plan response/lifecycle and T022–T023 provide a durable non-success outcome with no authoritative partial findings. |
| Idempotency cannot replay a different request | Pass at persistence primitive; integration pending | The SQLite run store binds the canonical digest, run payload, and key in one transaction; HTTP 409 mapping and endpoint integration remain implementation tasks. |
| Specs 001–003 interfaces compose | Contract mapping pass; runtime integration pending | [compatibility-review.md](compatibility-review.md) maps source, note, extraction, claim, resident, and claim-set identities; repository/service wiring remains unimplemented. |
| Acceptance scenarios are testable | Pass | EV-001 through EV-014 map to fixture task T024 and end-to-end task T025. |

## Non-blocking implementation decisions

The following are intentionally delegated to established repository architecture, not left as behavioral gaps:

- exact backend language/framework, persistence migration syntax, and test-file locations;
- selected approved model provider and deployment configuration;
- exact bounded timeout value and safe retry count for a verification run.

The execution mode is not deferred: this PoC is synchronous and returns a terminal HTTP 200 result. Each remaining implementation detail must preserve the public contract, lifecycle states, Unicode span semantics, and all-or-nothing safety guarantees. T001 resolves repository placement before code changes.

## Checklist gate

The checklist review is recorded in [checklist.md](checklist.md). The contract-level criteria are reviewed, while integration-test criteria remain explicitly open until the service, repositories, and API exist.

## Conclusion

The documents are internally consistent and have no unresolved product-policy ambiguity. Proceed with implementation only after repository architecture mapping and completion of the open integration-test criteria.
