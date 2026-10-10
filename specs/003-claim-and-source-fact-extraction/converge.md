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
| Scope control | Code inspection and tests show no transcript comparison, evidence verdict, diagnosis, or inferred treatment data. |
| Independent service testability | Service tests run without Spec 004. |
| Protected data handling | Redaction/telemetry tests and review pass. |
| Constitution contract stack | Pydantic contract tests, FastAPI/OpenAPI tests if exposed, SQLite repository tests, and an ADR for any material departure. |
| Synthetic-only/evaluation gate | Fixture audit plus a versioned 100+ scenario German benchmark, held-out policy, raw counts, configured Spec 008 threshold result, and disclosed regressions. |
| Run provenance/operability | Append-only run/version/body-hash history, explicit timeout/retry outcomes, idempotency, and permitted telemetry metrics. |

## Convergence procedure

1. Complete the dependency-ordered tasks and collect test evidence, including the required test-first fixtures before service implementation.
2. Compare implementation, tests, and public/internal interfaces to `spec.md`, `clarify.md`, and `plan.md`.
3. Append only newly discovered concrete gaps to `tasks.md`, with dependencies.
4. Implement those gaps and repeat the audit.
5. Report **Converged** only when every applicable check above has evidence and no task remains.
