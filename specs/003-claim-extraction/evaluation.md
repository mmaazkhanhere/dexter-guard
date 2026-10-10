# Spec 003 Feature-Level Evaluation

The implementation provides deterministic metric functions in
`src/claim_extraction/evaluation.py` and a versioned synthetic corpus in
`tests/evaluation/fixtures/spec_003_corpus.py`. The measured dimensions are
limited to claim identification precision/recall, atomicity, negation,
certainty, attribution, numerical extraction, character-span validity, and
structured-output success/failure rates.

The metrics do not assess clinical correctness, evidence support, contradiction,
diagnosis, approval, completeness, reviewer workload, or end-to-end reliability.

The local corpus contains 120 cases, source/evidence annotations, annotation
provenance, an explicit held-out policy, and a denominator policy. No benchmark result is
reported here: the repository currently has no populated Spec 008 shared
benchmark or executed annotated evaluation run. The fixture and metric APIs are
reproducible without network access or live providers and are ready for
registration when Spec 008 supplies its approved thresholds.
