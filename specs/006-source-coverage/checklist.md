# Spec 006 - Requirements Quality Checklist

**Reviewer-owned artifact:** Mark an item `[x]` only after an independent reviewer determines the requirement-quality criterion is met. Checked items do not indicate implementation completion. The implementation workflow must not modify this file.  
**Gate:** `implement.md` must not proceed while any item is unchecked.

## Completeness

- [x] CQ-001 The specification states the user value, FR-14 scope, dependencies, non-goals, and ownership boundaries with Specs 001-005 and 007-008.
- [x] CQ-002 The five coverage statuses are mutually exclusive, have precedence, and distinguish semantic uncertainty from operational failure.
- [x] CQ-003 Expected-fact extraction has an explicit source-only authority, valid-span requirement, atomicity rule, and safe unresolved-source outcome.
- [x] CQ-004 Material attributes and their required handling include negation, certainty, attribution, temporality, laterality, numerical value/unit/approximation, mobility assistance, and care actions.
- [x] CQ-005 The documented expectation policy states what enters the denominator and prevents the model from inventing severity.
- [x] CQ-006 Runtime counts and manually annotated held-out benchmark metrics have distinct definitions and denominators.
- [x] CQ-007 The public request/response and domain records are reference-only, versioned, and specify success/failure exclusivity.
- [x] CQ-008 Findings contain reviewable source references, derived quotes, candidate-claim references where applicable, and cannot auto-edit or approve a note.

## Clarity and safety

- [x] CQ-009 Source offsets use the project-wide Unicode code-point, start-inclusive/end-exclusive convention consistently.
- [x] CQ-010 `PARTIALLY_COVERED` versus `DISTORTED` is unambiguous, including a missing laterality and lost uncertainty example.
- [x] CQ-011 A faithful duplicate claim prevents a false omission finding while an independent distorted duplicate remains linked for review.
- [x] CQ-012 Unresolved extraction does not invent a source fact and does not inflate or deflate the completeness denominator.
- [x] CQ-013 Invalid provenance, stale revisions, malformed provider output, span failures, missing assessment closure, and unavailable dependencies fail safely.
- [x] CQ-014 Spec 006 does not duplicate Spec 004 evidence classification, Spec 005 deterministic numeric policy, or Spec 007 severity/approval policy.
- [x] CQ-015 Re-evaluation semantics preserve old runs and require a new immutable note revision/claim set.

## Consistency and testability

- [x] CQ-016 `spec.md`, `clarify.md`, `data-model.md`, OpenAPI contract, plan, ADR 005, and tasks use the same status names, policy/version metadata, identifiers, idempotency rules, and denominator rules.
- [x] CQ-017 Every FR-14 requirement maps to one or more planned contract, unit, integration, acceptance, or evaluation-handoff tests.
- [x] CQ-018 COV-001 through COV-010 have explicit fixture expectations, including exact status, source/item reference, attributes, related findings, and denominator treatment.
- [x] CQ-019 Fixtures include German semantic paraphrase, multi-clause text, temporal modifiers, approximate measurement, indirect speech, explicit negation, uncertainty, and Unicode span boundaries.
- [x] CQ-020 The plan demonstrates deterministic boundary validation around an untrusted semantic extractor/matcher and prohibits network/LLM use in contract integrity checks.
- [x] CQ-021 Evaluation handoff preserves source text, manually annotated expected facts, claim-level outcomes, source evidence, materiality/severity labels, annotation provenance/dispute resolution, policy/dataset versions, raw counts for all constitution metrics, and held-out split protection.

