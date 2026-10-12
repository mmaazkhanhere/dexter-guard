# Spec 005 — Requirements Quality Checklist

**Reviewer-owned artifact:** Mark an item `[x]` only after a reviewer determines the requirement-quality criterion is satisfied. Checked items do not indicate implementation completion.  
**Gate:** `implement.md` must not proceed while any item remains unchecked.

## Completeness

- [ ] CQ-001 The specification states the user value, scope, non-goals, and ownership boundaries for FR-11 and FR-16.
- [ ] CQ-002 Every rule (`NUM-001`–`NUM-005`, `STR-001`–`STR-003`, `EVD-001`–`EVD-003`) has an unambiguous trigger, outcome, and acceptance coverage.
- [ ] CQ-003 Source fact, claim, alignment, transcript, measurement, evidence-reference, run, and finding contracts are versioned and defined.
- [ ] CQ-004 All required result fields and null behavior for unavailable expected/observed values are specified.
- [ ] CQ-005 The unit/category matrix, canonical units, and exact conversion factors are complete for the v1 PoC.
- [ ] CQ-006 All twelve supplied acceptance scenarios are represented with expected outcomes.

## Clarity and safety

- [ ] CQ-007 Alignment preconditions make it impossible for a numeric rule to infer semantic correspondence.
- [ ] CQ-008 `NOT_EVALUABLE`, `FAIL`, pass, and schema rejection are distinct and have no false-pass path.
- [ ] CQ-009 Approximation behavior relies only on structured data and does not infer German uncertainty from prose.
- [ ] CQ-010 Evidence-offset semantics and exact quotation matching agree with the architecture and Spec 004.
- [ ] CQ-011 Severity is explicitly a Spec 005 hint and final review/approval authority remains with Spec 007.
- [ ] CQ-012 No requirement permits diagnosis, plausible-range reasoning, auto-correction, or LLM outcome determination.

## Consistency and testability

- [ ] CQ-013 `spec.md`, `clarify.md`, `data-model.md`, OpenAPI contract, plan, and tasks agree on rule IDs, units, outcomes, and versions.
- [ ] CQ-014 Each normative requirement has a planned executable unit, contract, integration, or acceptance test.
- [ ] CQ-015 Determinism has a repeatability assertion, fixed ordering, exact decimal strategy, and no-network/no-LLM test.
- [ ] CQ-016 Spec 007 and Spec 008 consuming needs are concretely represented without assigning their policy/evaluation ownership to Spec 005.
- [ ] CQ-017 The ADR captures the cross-component semantic-alignment decision and alternatives.
- [ ] CQ-018 No unresolved ambiguity could change safety, evidence attribution, contract compatibility, or review behavior.
