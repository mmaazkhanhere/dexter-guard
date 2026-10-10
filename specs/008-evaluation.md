# Spec 003 Evaluation Contribution

This file is the bounded Spec 003 contribution to the shared evaluation
surface. It does not define system-wide reliability thresholds or replace the
approved Spec 008 benchmark owner.

## Synthetic cases

The labeled CLM-001–CLM-016 cases are defined in:

- `tests/claim_extraction/fixtures/claims.py`
- `tests/evaluation/fixtures/spec_003_claims.py`

They cover atomicity, negation, uncertainty, attribution, decimal commas,
units, medication details, revision isolation, empty/failure outcomes, invalid
spans, missing resident metadata, and provider timeout behavior.

## Feature-level metrics

`src/claim_extraction/evaluation.py` calculates:

- claim identification precision and recall;
- atomicity correctness;
- negation, certainty, and attribution accuracy;
- numerical extraction accuracy;
- character-span validity;
- structured-output success and failure rates.

These metrics measure extraction behavior only. They do not measure clinical
correctness, evidence support, contradiction, diagnosis, approval, completeness,
reviewer workload, or end-to-end reliability.

No threshold or measured result is claimed until the shared benchmark owner
provides an approved corpus, held-out split, denominator policy, and release
thresholds.
