# Requirements Quality Checklist: Nursing Note Generation

**Reviewer-owned artifact.** Check an item only after reviewing the requirements-quality criterion. A checked box does not mean implementation is complete.

## Scope and ownership

- [ ] FR-02 through FR-05 are stated in testable language with observable outcomes.
- [ ] Spec 001 dependency (FR-01) is clearly excluded from this feature's implementation scope.
- [ ] Verification, approval, diagnosis, and treatment recommendations are explicitly out of scope.
- [ ] Generated and imported notes are unambiguously constrained to the `DRAFT` lifecycle state.

## Completeness and clarity

- [ ] Both generation and external-import paths specify their inputs, outputs, provenance, and failure behavior.
- [ ] Structured facts identify the required types and fidelity fields, including source anchors.
- [ ] Revision and origin metadata requirements are sufficient for a downstream consumer to distinguish generated from imported content.
- [ ] The specification states what must happen when source details are missing or contradictory.
- [ ] The specification does not imply an unowned UI, authorization, retention, or verification requirement.

## Fidelity and safety

- [ ] Negation, uncertainty, attribution, values, and units have explicit preservation requirements.
- [ ] The specification prevents unsupported diagnosis and fabricated observations/actions.
- [ ] A malformed model response cannot be mistaken for a successful note.

## Acceptance quality

- [ ] GEN-001 through GEN-010 are independently testable and map to FR-02 through FR-05.
- [ ] Regression cases assert semantic preservation rather than grammatical quality alone.
- [ ] Import behavior explicitly proves that generation is not invoked.
- [ ] Success criteria are measurable and do not claim downstream reliability work is complete.
