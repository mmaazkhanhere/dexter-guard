# Specify Record — Spec 003

## Feature statement

Provide a reliable, source-independent engine that turns a German nursing note into independently addressable, atomic factual claims for later verification. The engine captures the candidate note's assertions exactly; it never judges them against a caregiver transcript and never performs diagnosis.

## Why this feature exists

Verification can only be precise when its inputs are discrete, locatable assertions. A whole nursing note cannot reliably be marked supported or contradicted when it contains several observations, reports, measurements, and conclusions. This feature supplies the stable claim boundary between note production/import (Spec 002) and evidence verification (Spec 004).

## Constitution alignment record

The **AI Nursing Documentation Reliability Engine Constitution v1.0.0** is governing guidance and is not modified by this feature. This feature is evaluated against its evidence fidelity, human authority, spec-first delivery, contract-first architecture, evaluation, privacy/provenance, and observable-failure requirements.

Spec 003 provides candidate-note provenance and atomicity. It deliberately does **not** claim source-transcript support: Spec 004 attaches and validates transcript evidence before a claim may receive an evidence outcome. Spec 003 must fail closed on malformed extraction rather than make an unsupported claim appear verified.

The implementation plan contains the mandatory principle-by-principle Constitution Check. Any stricter constitutional requirement prevails and requires corresponding specification, test, and traceability updates before implementation.

## Inputs, output, and boundaries

- Input: one immutable, stored German nursing-note revision from Spec 002 or an import workflow.
- Output: `ExtractionResult` and zero or more `Claim` records defined in `spec.md`.
- Downstream: Spec 004 compares claims with evidence; Spec 005 consumes normalized attributes; Spec 007 uses locations for highlighting.
- Excluded: evidence status, transcript retrieval, contradiction detection, scoring, diagnosis, and clinical recommendations.

## Product outcome

FR-06 is satisfied when every factual assertion that is eligible for later source verification is represented by an independently addressable claim whose text and semantic cues can be traced to the exact submitted note revision.
