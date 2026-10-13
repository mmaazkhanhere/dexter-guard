# Spec 008 Technical Plan — Evaluation and Observability

**Inputs:** [spec.md](spec.md), [clarify.md](clarify.md), [data-model.md](data-model.md), constitution, architecture, and Specs 001–007.  
**Outcome:** A local, reproducible, headless-first measurement system that invokes the existing reliability pipeline, persists non-sensitive experiment provenance, and exposes diagnostic reports.

## Technical context

| Concern | Selected design |
| --- | --- |
| Runtime | Existing Python 3.11+ package layout, FastAPI, Pydantic v2, pytest. |
| Persistence | Existing repository pattern and local SQLite; immutable benchmark manifests and append-only evaluation-run records. |
| Existing pipeline | Spec 003 extraction → 004 evidence verification → 005 deterministic validation → 006 coverage; Spec 007 only for observed/simulated review-outcome capture. |
| UI | Lightweight React report surface only if/when the project’s React host exists; headless JSON/CLI service is the required execution path. |
| Statistics | Pure-Python deterministic metric/matching functions; Wilson 95% intervals; optional seeded bootstrap for paired/latency summaries. |
| Data protection | Synthetic German fixtures only; content-free telemetry; transcript/note text is never copied to logs. |

## Architecture and boundaries

    versioned benchmark manifest
           │
           ▼
    DatasetValidator ──> SplitProtector ──> EvaluationRunner (headless)
                                                  │
                 ┌────────────────────────────────┼─────────────────────────┐
                 ▼                                ▼                         ▼
         existing pipeline ports           Match + metrics            RunRepository
      (003 / 004 / 005 / 006)              (pure functions)           (SQLite/JSON)
                 │                                │                         │
                 └──────────────► case result ◄───┘                         ▼
                                                                      ReportQueryService
                                                                      ├─ machine JSON/CSV
                                                                      └─ lightweight UI/API

| Component | Responsibility | Must not do |
| --- | --- | --- |
| Dataset repository/validator | Load immutable versioned synthetic fixtures; validate hashes, spans, annotations, category coverage, 100+ count, and split/family integrity. | Tune prompts/rules, create source alternatives, or accept real data. |
| Split protector | Select one explicit split and prevent held-out families/duplicates entering tuning paths. | Silently use all splits or waive a conflict. |
| Pipeline adapter | Construct normal immutable references and invoke existing components. | Duplicate extraction, semantic verification, deterministic rules, coverage assessment, or review approval. |
| Evaluation runner | Coordinate each fixed candidate, capture stage results/timing/cost, produce terminal case/run results. | Mutate candidate/source/review state or hide partial failure. |
| Matching/metrics services | Deterministically match findings and compute documented measures. | Infer ground truth, alter producer results, or award duplicate credit. |
| Experiment repository | Persist append-only configurations, case results, aggregates, exports, and failure records. | Overwrite an executed result. |
| Report query/UI | Provide diagnostic drill-down and historical/live distinction. | Claim clinical safety or treat a saved result as new inference. |

## Runner workflow

1. Load dataset by exact ID/version/hash and require an explicit split.
2. Validate the complete dataset plus selected-split integrity before any provider call. Reject invalid datasets with INVALID_DATASET.
3. Materialise fixed source/candidate identities in a clean evaluation namespace or fixture repository; verify body/source hashes.
4. Invoke the configured existing pipeline using its normal contracts. Capture extraction, evidence, deterministic, coverage, and optional review artifacts as immutable references.
5. For each terminal case, normalise upstream findings into ObservedFinding without changing owner-specific meanings. Capture per-stage and end-to-end duration, tokens, costs, retries, and typed failures.
6. Run EVALUATION_MATCHING-v1 once against manual annotations; calculate case scores and completeness from annotated expected facts, never Spec 006 runtime completeness.
7. Aggregate exact raw counts, confidence intervals, failure/unscorable counts, latency/cost, warning counts, and category breakdowns. Persist the terminal EvaluationRun.
8. Emit a JSON report plus concise human-readable summary. A report must include its configuration/run identity and be reproducible from persisted inputs.
9. If paired comparison is requested, validate matching candidate hashes and task conditions before calculating deltas. Keep observed human review, simulated review, and automated detection separate.

Timeouts, provider unavailability, malformed outputs, invalid spans, interrupted processes, and persistence failures produce an explicit terminal state. Partial case records are retained whenever durably available. Retries rely on upstream idempotency keys; the runner must not duplicate review decisions or alter notes.

## Benchmark and annotation strategy

The repository shall add an immutable data/evaluation/<dataset-version>/ manifest with synthetic source/candidate fixture references, an annotation guide, hashes, and split manifest. The authoring workflow is:

1. Create scenario and family identifiers before assigning split.
2. Annotate source facts/spans, atomic claims, error instances, expected statuses/evidence relations, severity, and applicability with the approved guide.
3. Independently review/dispute annotations; retain provenance and resolution.
4. Run validator for schema, spans, source/note hashes, IDs, duplicate/family integrity, category coverage, and at least 100 scenarios.
5. Mark accepted only after the reviewer records the dataset version/hash and held-out protection result.

Scenario distribution is a coverage requirement, not a per-category numerical quota. The validator must prove at least one accepted scenario for every required category and multiple-error/ambiguous/paraphrase cases.

## Interfaces and persistence

Implement Pydantic domain models from [data-model.md](data-model.md) and an API surface described by [contracts/evaluation.openapi.yaml](contracts/evaluation.openapi.yaml). Provide a Python-callable runner/CLI as the canonical automation interface; HTTP is a query/control façade, not a prerequisite for CI.

Suggested local records: evaluation_dataset, evaluation_case_snapshot, evaluation_run, evaluation_case_result, evaluation_observed_finding, evaluation_ground_truth_match, evaluation_metric, evaluation_comparison, and evaluation_export. Enforce immutable run insertions, unique dataset-version/scenario, unique error/finding match consumption within a case, and source/note/revision/hash consistency.

Exact existing ports/routes, current app composition, provider timeout/retry budgets, React host, and SQLite migration convention are not established by the planning materials. T001–T002 are mandatory discovery gates. They must produce a compatibility record before code or contract wiring; this plan does not invent missing APIs.

## Observability

For each evaluation attempt record: run/correlation IDs; dataset identity/hash/split; code/contract/configuration versions; stage status; safe failure code; timestamps/duration; token/cost/pricing metadata; warning category/count; match counts; and export/report identity. Logs/metrics contain no transcript, note, prompt, raw provider output, credentials, or real healthcare data.

Cost is additional verification cost only: extraction/verification/deterministic/coverage calls attributable to evaluation, excluding initial candidate generation. Each cost record identifies currency, pricing assumptions version, token source, and AVAILABLE/UNAVAILABLE state.

## Report design

The report has run selection, provenance header, aggregate metric cards with numerator/denominator/interval/state, baseline-vs-validated panel, category/failure breakdowns, missed-critical and false-positive/negative lists, latency/cost summaries, and a case drill-down. Drill-down links IDs/hashes to findings, match decision, expected annotation, and safe source/claim references. JSON and CSV exports must preserve all raw counts and IDs; no export implies fresh execution.

## Test strategy

| Level | Required proof |
| --- | --- |
| Unit | Dataset integrity rules; matching permutations/tie breaks; zero denominators; metrics; Wilson interval; cost/latency aggregation; pairing validity; status transitions. |
| Contract | Pydantic/OpenAPI validation, terminal-state exclusivity, immutable provenance, export shape, and typed error body. |
| Repository | Append-only run persistence, historical retrieval, restart durability, idempotency, hash/split constraints. |
| Integration | Adapters to 003–006 through fakes then verified actual ports; no frontend dependency; failure/timeout/malformed-output preservation. |
| Acceptance | EVAL-001 through EVAL-016 and 100+ benchmark acceptance. |
| Regression | Deterministic mocked CI benchmark; reference-run comparison; live-model variability report, never a deterministic CI assertion. |

## Constitution check

| Principle | Planned control | Status |
| --- | --- | --- |
| Evidence fidelity | Immutable source/hash/span and target-aware matching; no candidate as evidence. | Pass by plan |
| Human authority | Measurement does not approve, repair, or alter notes; observed review is separately represented. | Pass by plan |
| Specification-first | Requirements, clarification, model, contract, plan, tasks, analysis, and reviewer gate precede code. | Pass by plan |
| Contract-first/modular | Pydantic models, repository/adapter ports, no duplicated reliability algorithms. | Conditional on T001–T002 compatibility evidence |
| Evaluation rigor | Versioned 100+ benchmark, held-out protection, raw counts, uncertainty, regression visibility. | Pass by plan |
| Privacy/provenance | Synthetic-only immutable fixtures/runs and content-minimised telemetry. | Pass by plan |
| Observable failure | Typed partial/failed/interrupted results, no silent exclusions. | Pass by plan |

## Trade-offs

- SQLite plus immutable JSON exports gives a small reproducible PoC, at the cost of local-scale query performance.
- Headless-first execution ensures CI/reproducibility, while the optional React report avoids blocking measurement on UI availability.
- Deterministic fixture runs make regression tests stable; live-model runs remain necessary for real behavior but report variability rather than hiding it.
- Manual ground truth is essential for credible scoring, even though it costs annotation/review effort; inferred labels would invalidate the benchmark.

