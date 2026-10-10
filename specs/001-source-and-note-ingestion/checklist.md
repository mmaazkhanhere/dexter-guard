# Requirements Quality Checklist: Source Transcript Ingestion and Evidence Reference Foundation

**Purpose**: Validate that the requirements are complete, clear, consistent, and ready for implementation.

**Created**: 2026-10-10

**Feature**: [spec.md](./spec.md)

## Ownership and checkbox semantics

This is a reviewer-owned requirements-quality artifact. Mark `[x]` only when the reviewer determines that the requirement-quality criterion is satisfied. A checked item does not mean that implementation work is complete.

`implement.md` reads these markers as a gate but must not change them. The reviewer owns all checkbox changes.

## Scope and user value

- [ ] CHK001 Does the feature name accurately describe source transcript ingestion and evidence-reference foundations rather than external nursing-note ingestion?
- [ ] CHK002 Does the scope explicitly assign `NursingNote` ingestion and note-specific behavior to a later specification?
- [ ] CHK003 Are audio input, speech recognition, multi-resident processing, clinical reasoning, authentication, and LLM-backed validation explicitly excluded?
- [ ] CHK004 Does each P1 user story describe a distinct user value and remain independently testable?

## Requirement clarity

- [ ] CHK005 Is FR-01 traced to a specific structured input shape and acceptance scenario?
- [ ] CHK006 Is “one synthetic resident” limited to enforceable structured-input rules rather than semantic transcript inference?
- [ ] CHK007 Are blank, whitespace-only, non-text, malformed, unsupported, and structurally invalid submissions distinguished clearly enough to test?
- [ ] CHK008 Are source ID creation, version `1`, revision creation, and retrieval semantics unambiguous?
- [ ] CHK009 Is the stale/concurrent revision behavior defined with a stable conflict outcome and no partial persistence?
- [ ] CHK010 Is the structured error shape and minimum error-code vocabulary specified consistently?

## Evidence and Unicode integrity

- [ ] CHK011 Does the specification define source identity as `(source_id, source_version)` everywhere evidence is referenced?
- [ ] CHK012 Does it state that transcript text is preserved exactly without Unicode or line-ending normalization?
- [ ] CHK013 Are span offsets explicitly defined as zero-based Unicode scalar-value/code-point indices rather than bytes, UTF-16 units, or grapheme clusters?
- [ ] CHK014 Are `start` inclusive and `end` exclusive stated consistently in the spec, data model, API contract, and tests?
- [ ] CHK015 Are combining marks, grapheme clusters, CRLF/LF, non-ASCII characters, empty spans, reversed spans, and out-of-range spans covered?
- [ ] CHK016 Does the spec prevent copied excerpts from becoming authoritative without their source reference?
- [ ] CHK017 Does it prohibit silent cross-version evidence redirection?

## Contract and artifact consistency

- [ ] CHK018 Do `spec.md`, `data-model.md`, `data_model.md`, and `source-api.yaml` agree on required `SourceDocument` fields?
- [ ] CHK019 Do the API schemas agree with the versioning rule, including `expected_source_version` and inherited resident/language fields?
- [ ] CHK020 Do API error responses include all errors named by the requirements, including `VERSION_CONFLICT`?
- [ ] CHK021 Does `tasks.md` map every functional requirement and acceptance-critical invariant to a concrete task and test path?
- [ ] CHK022 Does `plan.md` record technical context, constitution checks, design decisions, and unresolved assumptions without changing user-facing intent?
- [ ] CHK023 Are task IDs, story labels, dependencies, parallel markers, and exact file paths valid under the selected Spec Kit convention?

## Readiness and testability

- [ ] CHK024 Can every acceptance scenario be verified deterministically without an LLM provider, external network, or medical judgment?
- [ ] CHK025 Are atomicity and concurrent revision outcomes testable independently of the storage implementation?
- [ ] CHK026 Are retrieval and historical-version requirements measurable without relying on internal implementation details?
- [ ] CHK027 Are all remaining ambiguities either resolved in `clarify.md` or recorded with a safe default and owner?
- [ ] CHK028 Does the specification avoid prescribing implementation details where a behavior or contract is sufficient?
- [ ] CHK029 Is the implementation gate explicit that unchecked checklist items require reviewer confirmation before proceeding?

## Notes

Reviewers should record findings below, including the checklist ID, the affected artifact, the ambiguity or inconsistency, and the required source-of-truth update.

```text
Reviewer:
Date:
Findings:
Required follow-up:
```
