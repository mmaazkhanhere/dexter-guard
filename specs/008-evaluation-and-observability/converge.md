# Spec 008 Convergence Procedure

## Purpose

Determine whether the implemented evaluation and observability feature satisfies its approved requirements, design artifacts, and tasks. This is a verification procedure, not an implementation claim.

## Inputs

Review the current constitution; spec.md; clarify.md; data-model.md; API contract; plan.md; tasks.md; analyze.md; reviewer checklist; benchmark annotation guide/manifests; accepted dataset; code; tests; and persisted/reproducible reports. Record the exact repository revision and artifact/dataset/configuration versions.

## Convergence gates

### A. Requirements and reviewer gate

- Confirm independent reviewer approval of every applicable checklist item.
- Trace FR-26 through FR-33 and EVAL-001 through EVAL-016 to code, test evidence, and results.
- Confirm every required task is complete or has a documented not-applicable rationale approved by the reviewer.

### B. Dataset and held-out integrity

- Validate at least 100 synthetic German scenarios, all required category coverage, annotation provenance, IDs/hashes, exact source spans, multiple candidates where applicable, and no real data.
- Verify every scenario/family is in exactly one split; exercise duplicate/near-duplicate and family-crossing rejection.
- Confirm held-out data was not used in prompt/model/rule tuning or model selection, using run/configuration/audit evidence.

### C. Measurement correctness

- Exercise exact target-aware matching, multiple/duplicate findings, one-to-many attempts, unrelated/incorrect-location warnings, unsupported-versus-contradicted classification, and partially correct findings.
- Recalculate each aggregate from saved case results and verify raw numerator/denominator values, zero-denominator treatment, failures/unscorable counts, confidence intervals, latency percentiles, and cost availability states.
- Confirm benchmark completeness uses manual annotations, not runtime completeness.
- Confirm critical-error recall is evaluated against the approved held-out >=95% criterion. Confirm no unapproved metric threshold is represented as a gate.

### D. Runner, provenance, and failure safety

- Run deterministic headless fixtures with mocked/saved provider responses; verify byte-stable matching/metric outputs where expected.
- Test invalid dataset, mismatched source/note/hash, invalid span, timeout, unavailable provider, malformed model output, persistence failure, interruption, retry, and idempotency paths.
- Confirm no failed/invalid/incomplete run is displayed as successful and no case is silently removed.
- Inspect telemetry/exports for complete configuration provenance and absence of source/note/prompt/raw-output content.

### E. Reporting and paired comparison

- Verify report/API selection and export of historical runs, synthetic provenance, drill-down from every aggregate item to case/finding/match/reference, category/failure views, cost/latency, missed critical cases, and saved/live distinction.
- Verify paired baseline/validated candidates have identical candidate/source/task hashes and baseline lacks reliability findings.
- Confirm observed human review, simulated review, automated detection, starting quality, final quality, and burden remain separately labelled.

## Evidence ledger

Create or update a dated convergence report with one row per requirement, invariant, acceptance scenario, task, and test command:

| ID | Artifact | Code/test/report evidence | Result | Gap/next action |
| --- | --- | --- | --- | --- |
| FR-26 | spec.md | _populate at review_ | NOT RUN | _populate_ |

Permitted result values are PASS, FAIL, BLOCKED, NOT RUN, and NOT APPLICABLE with rationale. Evidence must remain synthetic-only and content-minimised.

## Gap handling and decision

For every non-passing implementation/test gap, append one concrete unchecked task in tasks.md with the requirement, observed evidence, dependency, target component, and acceptance proof. Do not amend requirements merely to match current code. Re-run affected and full applicable evidence after remediation.

Report **CONVERGED** only when all applicable gates pass, the independent checklist is approved, every required task has evidence, the accepted benchmark has 100+ valid scenarios, held-out protection is demonstrated, and no unresolved regression/failure/documented contract drift remains. Otherwise report **NOT CONVERGED** with exact blockers. Convergence never claims clinical safety or broader product readiness.

