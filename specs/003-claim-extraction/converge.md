# Convergence Audit — Spec 003

**Audit state:** Pre-implementation baseline  
**Result:** Not converged — implementation and automated-test evidence have not yet been produced. No additional tasks are appended because this task created planning artifacts only.

## Required convergence checks after implementation

| Check | Required evidence |
|---|---|
| FR-06 atomic addressability | Passing CLM acceptance suite with one independently addressable id per factual claim. |
| Semantic fidelity | Tests prove negation, certainty, attribution, numeric, medication, and temporal rules. |
| Location integrity | Span validation against stored revision, including Unicode/code-point and UTF-16 cases. |
| Revision isolation | Tests prove edited revisions cannot reuse earlier claims/results. |
| Failure visibility | Malformed/invalid provider outputs yield explicit errors and no partial result. |
| Typed failure integrity | Pydantic discriminated-union tests prove every `FAILED` result has a typed error and `SUCCEEDED`/`EMPTY` results cannot contain one. |
| Scope control | Code inspection and tests show no transcript comparison, evidence verdict, diagnosis, or inferred treatment data. |
| Independent service testability | Service tests run without Spec 004. |
| Protected data handling | Redaction/telemetry tests and review pass. |
| Constitution contract stack | Pydantic contract tests, FastAPI/OpenAPI tests if exposed, SQLite repository tests, and an ADR for any material departure. |
| Synthetic-only/evaluation gate | Fixture audit plus a versioned 100+ scenario German benchmark, held-out policy, raw counts, configured Spec 008 threshold result, and disclosed regressions. |
| Run provenance/operability | Append-only run/version/body-hash history, explicit timeout/retry outcomes, idempotency, and permitted telemetry metrics. |
| Evidence handoff | Every successful/empty result has immutable source-reference metadata and is retrievable by typed service/persisted record for Spec 004. |
| Extraction evaluation | Shared-benchmark contributions and extraction precision/recall, span-validity, semantic-attribute, and failure-handling results are recorded. |

## Convergence procedure

1. Complete the dependency-ordered tasks and collect test evidence, including the required test-first fixtures before service implementation.
2. Compare implementation, tests, and public/internal interfaces to `spec.md`, `data-model.md`, `clarify.md`, and `plan.md`.
3. Append only newly discovered concrete gaps to `tasks.md`, with dependencies.
4. Implement those gaps and repeat the audit.
5. Report **Converged** only when every applicable check above has evidence and no task remains.

## Post-implementation evidence

The core implementation is partially converged: contracts, revision-bound
service behavior, fail-safe provider handling, SQLite persistence, and
deterministic focused/full test evidence exist. Shared Spec 008 registration
and complete CLM-001â€“016 acceptance execution remain pending because those
downstream artifacts are not present in this repository.

- `pytest -q tests/claim_extraction`: 31 passed.
- `pytest -q`: 89 passed, with one pre-existing Starlette/httpx deprecation warning.
- `src/claim_extraction/evaluation.py` provides reproducible feature-level
  metric calculations, but no measured benchmark values are claimed without an
  annotated evaluation run.
- The optional HTTP adapter was not exposed; the mandatory typed service and
  current-result repository handoff are implemented.
