# Spec 004 evaluation handoff

## Versioned inputs

- Critical-case manifest: [`ev-001-014-v1.json`](../../specs/004-evidence-verification/fixtures/ev-001-014-v1.json)
- Development report: [`spec004-development-evaluation-v1.json`](../../specs/004-evidence-verification/evaluation/spec004-development-evaluation-v1.json)
- Report schema: [`development-evaluation-report.schema.json`](../../specs/004-evidence-verification/contracts/development-evaluation-report.schema.json)
- Executable fixture and API coverage: `tests/evidence_verification/test_acceptance_fixtures.py`, `test_e2e_acceptance.py`, and `test_fixture_manifest.py`

The manifest contains synthetic German source snapshots, immutable claim text,
expected primary status, required discrepancy labels, and the evidence-span or
failure rule for EV-001 through EV-014. It is versioned independently of model
output and uses `EVIDENCE_ANNOTATION-v1` and `EVIDENCE_STATUS-v1`.

## Development report interpretation

`spec004-development-evaluation-v1.json` records the deterministic fixture
verifier run over the eleven semantic cases (the three deliberate failure
cases are reported by the regression suite). It includes exact classification
accuracy, critical-error recall, supported-claim false-positive rate, and
evidence-grounding validity with numerators and denominators. Explanation
wording is intentionally not measured.

This report is a development acceptance artifact only. It is not a production
quality claim, does not use held-out data, and does not replace Spec 008’s
evaluation or release thresholds. Before enabling an external configured LLM,
rerun the same manifest with the approved provider and record its model,
prompt, policy, evaluator, dataset, and failure versions in a new report.

## Handoff invariants

1. A finding is counted as grounded only when its source span and derived quote
   resolve against the immutable source snapshot.
2. Provider failures, stale provenance, and persistence failures are excluded
   from semantic classification metrics and must remain non-authoritative.
3. Supported false positives are computed only among predictions with primary
   status `SUPPORTED`.
4. Critical-case recall uses the manifest’s labelled critical cases, not a
   future held-out benchmark.

