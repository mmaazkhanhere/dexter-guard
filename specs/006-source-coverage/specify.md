# Spec 006 - Source Coverage & Completeness Verification: Initial Feature Brief

## Problem

A nursing note can contain only source-supported statements and still omit an important fact stated by the caregiver. Evidence verification in Spec 004 evaluates note-to-source support. This feature adds the inverse source-to-note check so a materially incomplete German nursing note is visible to a caregiver before approval.

## Desired outcome

For an immutable German caregiver transcript and an exact candidate nursing-note revision, identify important, explicitly stated source facts and report whether each is faithfully represented, partly represented, absent, distorted, or impossible to assess reliably.

## In scope

- Extract atomic source facts for symptoms, explicitly negated symptoms, numerical measurements, mobility observations, care actions, and explicitly stated uncertainty.
- Anchor every extracted fact to valid spans in the immutable transcript version.
- Compare each expected source fact with atomic claims from the candidate note using semantic equivalence rather than exact wording alone.
- Classify source-fact coverage as `COVERED`, `PARTIALLY_COVERED`, `MISSING`, `DISTORTED`, or `UNCERTAIN`.
- Preserve importance and policy inputs for downstream severity mapping.
- Produce source-grounded, actionable review findings; retain links to overlapping Spec 004 contradiction findings.
- Re-evaluate a new immutable note revision without modifying a prior coverage run or note.
- Supply synthetic German acceptance fixtures and benchmark handoff material.

## Out of scope

- Diagnosing a resident or judging whether an observation is medically true.
- Altering, completing, approving, rejecting, or silently repairing the nursing note.
- Treating every source phrase as mandatory note content.
- Choosing final clinical severity or approval effects; Spec 007 owns that policy.
- Using system-extracted facts as ground truth for held-out completeness evaluation; Spec 008 uses manual annotations.

## Initial acceptance cases

`COV-001` through `COV-011` cover faithful coverage, omitted temperature, lost laterality, German paraphrase, omitted negation, lost uncertainty, findings from an otherwise valid note, note-revision re-evaluation, unresolved source extraction, incompatible values, and faithful coverage alongside a contradictory duplicate. Fixtures also exercise multi-clause statements, temporal qualifiers, approximate measurements, indirect speech, and negation.

