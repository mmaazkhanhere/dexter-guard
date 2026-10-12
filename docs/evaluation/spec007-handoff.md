# Spec 007 Evaluation Handoff

**Status:** Planned dependency; no evaluation run is claimed by Feature 007 documentation.

Spec 007 supplies synthetic German human-review fixtures for HR-001–HR-018 and their expected
revision, finding, verification, approval, rejection, and audit outcomes. Spec 008 remains the
owner of the versioned benchmark and release evaluation.

Before any improvement or release claim, the Spec 008 package must provide:

- at least 100 versioned synthetic German scenarios, including correct cases and injected
  fabrication, numerical, negation, uncertainty, omission, resident-mixing, and unjustified-
  inference errors;
- source text, expected claim outcomes, evidence references, materiality/severity labels, and
  annotation provenance;
- model, prompt, ruleset, dataset, and contract versions for every run;
- held-out measurements for critical-error recall, false positives, claim classification,
  completeness, latency, inference cost, and reviewer workload;
- release thresholds and small-sample/repeated-run handling from `008-evaluation.md`.

The Spec 007 acceptance suite is a feature regression suite, not a substitute for the Spec 008
benchmark. This handoff is complete only when T003/T031 fixtures are registered by Spec 008 and
the resulting evaluation evidence is recorded in the implementation review.
