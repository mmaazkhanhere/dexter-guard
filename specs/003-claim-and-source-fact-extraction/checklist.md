# Requirements Quality Checklist — Spec 003

**Reviewer-owned artifact.** Check an item only after reviewing the specification and clarification decisions. Checked items confirm requirements quality; they do not mean implementation is complete.

## Scope and boundaries

- [ ] The scope identifies the candidate nursing note as the only factual source for this feature.
- [ ] The specification clearly excludes transcript comparison, evidence verdicts, contradiction detection, and diagnosis.
- [ ] The upstream/downstream Spec 002, 004, 005, and 007 relationships are clear.
- [ ] FR-06 has an unambiguous, testable outcome: each factual claim is individually addressable.
- [ ] The feature records candidate-note provenance without claiming transcript-evidence support before Spec 004.
- [ ] Each successful/empty result has immutable evidence-source metadata and a mandatory Spec 004 handoff event, without assigning an evidence verdict.
- [ ] Synthetic-only data and the absence of automatic approval/repair are explicit.

## Claim contract

- [ ] `Claim`, `TextSpan`, category, polarity, certainty, attribution, numeric, and result-state fields have clear meanings.
- [ ] Required versus optional fields are distinguishable without implementation guesswork.
- [ ] Revision ownership, id scope, and result status semantics are specified.
- [ ] Resident identity has explicit `IDENTIFIED`, `UNKNOWN`, and `AMBIGUOUS` handling.
- [ ] Validation-run, body-hash, schema, and provider/model/prompt version provenance is specified.
- [ ] The discriminated result contract requires typed errors for `FAILED` and forbids errors for `SUCCEEDED`/`EMPTY`.
- [ ] Offset conventions and substring-validation requirements are unambiguous.
- [ ] The contract has no field that implies evidence support, contradiction, or clinical validity.

## Semantic fidelity

- [ ] Atomicity says when to split and when not to split.
- [ ] Negation and its scope are explicitly preserved.
- [ ] Uncertainty and exact linguistic cues are explicitly preserved.
- [ ] Resident report, caregiver observation, and unspecified attribution are distinguishable.
- [ ] Numeric raw values, decimal normalization, units, ranges, and approximation rules are clear.
- [ ] Temporal and medication details cannot be inferred when absent.

## Failure behavior and lifecycle

- [ ] `SUCCEEDED`, `EMPTY`, and `FAILED` outcomes are mutually understandable and testable.
- [ ] Malformed provider output and invalid spans fail explicitly with no partial result.
- [ ] Ambiguous data cannot silently become invented structured detail.
- [ ] Edited revisions require new extraction before downstream verification.
- [ ] Sensitive-data logging boundaries are stated.
- [ ] Timeout, bounded retry, idempotent run, and unavailable-provider behavior is specified.
- [ ] Input-size limits, secret scanning, and dependency-vulnerability checks are specified.

## Acceptance coverage

- [ ] CLM-001 through CLM-016 cover the listed functional scenarios.
- [ ] Acceptance tests require semantic fidelity and spans, not merely parseable JSON.
- [ ] Tests establish independence from Spec 004.
- [ ] At least one test exercises Unicode-aware offset validation.
- [ ] A versioned synthetic 100+ scenario evaluation corpus includes source/evidence data, severity/materiality, annotation provenance, held-out policy, required metrics, and denominators.

## Cross-artifact review

- [ ] `plan.md` implements only the responsibilities described in `spec.md`.
- [ ] `tasks.md` has a dependency-ordered path for every requirement and acceptance scenario.
- [ ] Test/fixture tasks precede every corresponding implementation task.
- [ ] `analyze.md` records no unresolved contradiction, gap, or ambiguity.
- [ ] `plan.md` contains a Constitution Check for every constitutional core principle.
