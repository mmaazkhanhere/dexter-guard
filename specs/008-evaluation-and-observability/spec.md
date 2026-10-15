# Feature Specification: Evaluation and Observability

**Feature ID:** 008-evaluation-and-observability  
**Status:** Draft for independent requirements review  
**Primary requirements:** FR-26 through FR-33  
**Constitution baseline:** AI Nursing Documentation Reliability Engine Constitution v1.0.0  
**Upstream:** Specs 001–007  
**Scope:** Synthetic German nursing-documentation benchmark, reproducible evaluation, experiment tracking, and diagnostic reporting.

**Constitution filename mapping:** The constitution's reference to `008-evaluation.md` means this feature's canonical requirements file, `spec.md`, within the `specs/008-evaluation-and-observability` directory. No second requirements file is maintained; `specify.md` is the accompanying specify record.

## Purpose

Spec 008 measures whether the existing reliability engine improves fidelity of candidate nursing notes to their supplied German source transcripts. It provides reproducible evidence about detection quality, completeness, false positives, operational cost, latency, and review burden on a defined synthetic benchmark.

It does **not** establish medical truth, clinical safety, diagnostic accuracy, caregiver performance, or regulatory compliance. The system verifies transcript fidelity only. All benchmark, saved-example, live-evaluation, report, and telemetry data are synthetic.

## Scope and ownership

Spec 008 consumes immutable artifacts rather than reproducing their algorithms:

| Producer | Spec 008 consumes | Spec 008 must not do |
| --- | --- | --- |
| 001 | Immutable source ID/version/text hash and valid `SourceSpan` semantics | Create alternate sources or treat copied text as authority. |
| 002 | Immutable candidate-note identities and revisions | Generate or mutate candidate notes. |
| 003 | Atomic claims, extraction outcomes, and note spans | Re-extract claims as a substitute for the configured pipeline. |
| 004 | Evidence findings/statuses and verification run metadata | Reclassify evidence or make candidate text its own evidence. |
| 005 | Numeric/unit/structural findings and rule metadata | Reimplement deterministic validation. |
| 006 | Coverage assessments/findings and expected-fact metadata | Reassess source coverage. |
| 007 | Review decisions, revisions, full-note verification, and dispositions where a reviewed-workflow experiment is run | Approve/reject notes or infer review decisions. |

The feature includes a headless runner and a lightweight diagnostics report/dashboard. The report reads persisted evaluation data and does not change clinical workflow state.

## Definitions

- **Scenario:** One synthetic source-transcript situation with a stable `scenarioId`; it can contain multiple fixed candidate notes.
- **Candidate note:** A fixed note version evaluated against one scenario source. Evaluation never changes its text.
- **Annotated candidate claim:** A stable ground-truth reference to an atomic claim in a candidate note, with its expected primary evidence classification.
- **Ground-truth error instance:** One annotated, independently countable discrepancy tied to a candidate claim or missing source fact. Its ID is the sole denominator identity for error-detection metrics.
- **Critical error instance:** A ground-truth error instance whose approved severity is `CRITICAL`, using the reviewed severity policy version recorded in the fixture.
- **Expected source fact:** A manually annotated source fact applicable to completeness measurement; contextual or explicitly non-applicable facts are excluded from that denominator.
- **Detection:** A ground-truth error is detected only by a valid match to the affected annotated claim or missing fact and the required discrepancy; a nearby or unrelated warning does not count.
- **Baseline workflow:** The paired review path given the fixed candidate note without reliability findings.
- **Validated workflow:** The paired review path given the same fixed candidate note plus reliability-layer findings. It is not a claim that automation approved the note.
- **Saved example:** A versioned, immutable stored evaluation result/fixture selected for demonstration; it displays historical execution metadata.
- **Live evaluation:** A newly executed run against a versioned synthetic input; it receives a new run ID and execution timestamps.

## Functional requirements

### FR-26 — Synthetic Benchmark

1. The system shall maintain a versioned benchmark of at least 100 synthetic German-language scenarios.
2. Each scenario shall contain an immutable source-transcript reference, reference source facts and evidence spans, one or more fixed candidate nursing notes, annotated candidate claims, expected classifications, annotated error instances, applicable expected source facts, tags, split, annotation provenance, and dataset version.
3. The benchmark shall cover fully supported documentation; unsupported facts; explicit contradictions; numerical mismatches; unit mismatches; negation changes; uncertainty/certainty changes; attribution changes; unsupported clinical conclusions; important omissions; multiple errors in one note; ambiguous source evidence; and valid normalisation/harmless paraphrase.
4. Every annotation shall identify the affected claim or source fact, category, severity, expected evidence relationship/status, and source evidence correspondence when one is applicable.
5. A dataset validator shall reject duplicate IDs, invalid/mismatched spans, ambiguous denominator membership, missing required annotation provenance, unversioned policy references, invalid candidate/source lineage, and cases that violate the synthetic-only restriction.
6. A scenario may include multiple candidate notes only when each has its own stable candidate, claim, error, and expected-fact references.

7. The existing 100-scenario `008-v1` fixture shall remain the regression benchmark. A separate 30-scenario `008-curated-v1` companion corpus may be used only as a held-out, actual-verifier evaluation: it contains no development or validation cases, is reported under its own dataset identity, and its annotations remain `PENDING` until independent review is actually recorded. Its metrics must never be merged with saved-fixture results.

Resident-context mixing is an optional extension, not a minimum benchmark category. It may be enabled only when an existing upstream synthetic-context provenance contract is available. Such fixtures use one resident per transcript and a deliberately mismatched context/reference; they test provenance binding only and never require identifying or disambiguating multiple residents from transcript language. Optional extension cases must not be required for the core benchmark acceptance or release gate.

### FR-27 — Protected Held-Out Dataset

1. The benchmark shall use mutually exclusive `development`, `validation`, and `held_out` splits. Every scenario and candidate belongs to exactly one split.
2. A scenario family and closely related variants shall be assigned as a whole to one split. The dataset records a non-content `scenarioFamilyId` for split-integrity checking.
3. The runner shall require an explicit selected split and shall record it. It shall never silently fall back to all data.
4. Held-out fixtures, annotations, reports, and aggregate results shall not be inputs to prompt tuning, model selection, rule tuning, or threshold selection. Access for final evaluation/reporting is permitted, and every held-out run is auditable.
5. Dataset validation shall detect duplicate content hashes, candidate hashes, source hashes, or family IDs across splits unless an approved, documented exception identifies non-overlap and reviewer approval. No exception may place a close variant in held-out and a tuning split.

### FR-28 — Baseline-versus-Validated Comparison

1. The system shall support a paired protocol in which baseline and validated paths receive the same immutable candidate-note ID/body, source version, scenario, task instruction, and review task.
2. The baseline path shall not receive reliability findings, source-evidence recommendations derived by the reliability layer, or a proxy summary of either.
3. The validated path shall receive the recorded reliability-layer findings and the same other task materials available to baseline.
4. Starting-note quality, automated detection outcomes, human decisions, final reviewed-note quality, and review effort shall be stored and reported as separate measures.
5. When human review data is unavailable, the report shall show automated detection outcomes without asserting caregiver improvement. Any simulated review result must be labelled `SIMULATED`, identify its simulation policy/version, and remain separate from observed human results.
6. Pairing is invalid if candidates differ; invalid pairs remain visible and excluded from paired-effect calculations with an explicit reason.

### FR-29 — Reliability and Operational Metrics

The system shall calculate and report a typed metric result for every metric below. Every result shall include metric kind, state, scorable count, unscorable count, failed count, aggregation method, and policy version. Rate metrics shall include numerator, denominator, value, and confidence interval where meaningful; count metrics shall include count, note count, per-note value, and unit; duration/cost distributions shall include observation count, p50, p95, mean, unit, and currency where applicable. Percentages alone are insufficient.

| Metric | Required operational definition |
| --- | --- |
| Critical-error recall | Detected critical ground-truth error instances / all critical ground-truth error instances. |
| Supported-claim false-positive rate | Correctly supported annotated claims incorrectly flagged as requiring correction / all correctly supported annotated claims. `UNCERTAIN` unnecessarily routed to review counts as a false positive. |
| Claim classification accuracy | Correct primary evidence classifications / all annotated candidate claims. |
| Completeness | Expected source facts faithfully covered in the note / applicable expected source facts. |
| Scenario-level detection | Scenarios with every annotated critical error detected / scenarios containing critical errors. |
| Final-note quality | Remaining annotated factual errors and omissions after the review workflow, reported as counts and its explicitly stated denominator. |
| Review burden | Warnings, human decisions, and correction actions per note, reported individually and together. |
| Verification latency | End-to-end automated verification duration, reported as p50 and p95. |
| Additional inference cost | Verification-related model cost per note, excluding initial generation. |

Rules common to all metrics:

- Use the versioned matching policy consistently in every run.
- Missing evidence is not an explicit contradiction.
- A failure, timeout, invalid model output, interrupted run, invalid fixture, or unscorable item must be counted and listed; it must never disappear from the report.
- Rate/count denominators and distribution observation counts include only items whose definition makes them applicable. A zero denominator or observation count yields `NOT_APPLICABLE` with null derived values, raw zero counts, and a reason—not `0%`, `100%`, or zero cost.
- Failed execution does not create a guessed classification. It is excluded only from a classification/completeness denominator where no score is possible, while retained in failure counts and failure-rate reporting. Critical errors in a failed candidate are counted as not detected for critical-error recall unless an independent valid finding for that specific error was already persisted in the same declared evaluation attempt.
- Invalid or ambiguous ground truth makes the item `UNSCORABLE`; it is reported separately and blocks a release-quality conclusion for an affected selected split.
- Latency/cost summaries include successful and failed attempts separately. Percentiles are `NOT_APPLICABLE` when there are no completed observations; cost absent from a provider is `UNAVAILABLE`, not zero.
- Point estimates for rate metrics shall include a documented binomial confidence interval when the denominator is non-zero; the default reporting method is Wilson 95%. Bootstrap confidence intervals may additionally be used for paired deltas and median/p95 latency, with seed and resample count recorded.

The approved target is **critical-error recall ≥95% on the held-out benchmark**. No threshold for any other metric is introduced by this specification; all remain `TBD` until separately approved.

### FR-30 — Configuration Versioning

1. Every evaluation run shall record dataset ID/version/content hash, selected split, fixture/annotation policy versions, model provider/identifier/version, prompt IDs/hashes, inference parameters, rule/ruleset versions, application code revision, contract versions, matching-policy version, execution environment identity, timestamps, and execution status.
2. The runner shall record model token usage and estimated cost when available, alongside immutable pricing assumptions/currency and the calculation basis. It shall record `UNAVAILABLE` when the provider cannot supply an input.
3. Configuration provenance shall be immutable after a run becomes terminal. A new execution creates a new run; it does not overwrite historical results.

### FR-31 — Automated Regression Testing

1. The runner shall execute headlessly without the React interface and emit machine-readable results suitable for CI.
2. Deterministic fixture/mock-provider runs shall be repeatable and shall test benchmark validation, split integrity, matching, metrics, configuration capture, failures, and report consistency.
3. Live model evaluations remain available but are explicitly marked non-deterministic. Prompt, model, inference, and rules changes shall trigger a recorded comparison against an approved reference run on the applicable protected split.
4. A regression is an observed decline against an approved target/guardrail or a statistically/investigatively material change that lacks an approved disposition. Unapproved metric thresholds are not invented; their comparison is reported as `REVIEW_REQUIRED`.
5. Failed benchmark execution, missing baseline/reference, unresolved regression, or unsupported configuration comparison shall be visible as a non-successful evaluation outcome, never a passing result.

### FR-32 — Evaluation Results

1. A lightweight report/dashboard shall permit evaluation-run selection and display configuration, dataset identity, aggregate metrics, confidence/denominator information, paired comparison, error-category breakdowns, false-positive/false-negative analyses, missed critical errors, latency/cost summaries, failures, and export controls.
2. Case inspection shall trace every aggregate numerator/denominator item to scenario, candidate, ground-truth ID, pipeline findings, match disposition, and relevant immutable source/claim references.
3. The report shall clearly distinguish saved historical results from a live execution and shall preserve original run timestamps/statuses.
4. The interface prioritises diagnostic clarity, accessible text labels, and auditability over visual sophistication. It must not display a clinical-safety claim.

### FR-33 — Live and Saved Examples

1. The system shall support execution against a selected synthetic benchmark candidate and inspection of saved versioned examples.
2. The system may also track a fresh synthetic demonstration input created or imported through Specs 001–007. Spec 008 shall accept immutable source, note, and upstream-run references for that demonstration; it shall not accept arbitrary transcript/note text or create a duplicate generation or ingestion workflow.
3. A live execution shall use the normal configured reliability pipeline, generate a new `EvaluationRun`, retain its configuration/status, and be labelled `NEWLY_EXECUTED`. Benchmark executions are scored; demonstration tracking is labelled `DEMONSTRATION_ONLY` and is not used as benchmark evidence.
4. A saved example shall retain the original evaluation run/result identity and be labelled `HISTORICAL_SAVED_RESULT`; it shall never be represented as fresh inference.
5. Both modes shall show synthetic-only provenance and must not accept real patient content.

## Ground-truth matching and scoring

The matching policy is versioned as `EVALUATION_MATCHING-v1` and is defined in detail in `data-model.md`.

1. A detected finding validly matches an annotated error only when it identifies the same candidate claim or missing expected source fact, compatible producer/error type, the relevant conflicting semantic attribute/value where applicable, expected evidence status, and required source-evidence correspondence.
2. A finding may match at most one ground-truth error instance; an error instance may be detected once. Multiple qualifying findings select the highest-specificity match and remaining warnings are duplicates/unmatched. Tie-breaking is deterministic and recorded.
3. One broad finding may match one error only. It cannot receive credit for multiple errors unless the producer contract itself exposes separate affected IDs and the annotation has separate corresponding findings.
4. A status-only warning without the affected claim/fact or relevant discrepancy is not a detection. Incorrectly located warnings and unrelated warnings are false positives where their producer requires review; they never offset false negatives.
5. `UNSUPPORTED` and `CONTRADICTED` are incompatible for exact primary-classification scoring. `UNCERTAIN` does not equal either. Missing source evidence must remain `UNSUPPORTED` where appropriate and never be upgraded to `CONTRADICTED` merely to match an error label.
6. A partially correct finding with the right affected target but wrong error type, status, or material attribute is a target-linked misclassification: it is not detected for recall, is recorded for failure analysis, and is not double-counted as an unrelated warning.
7. Duplicate warnings beyond the accepted match are reported separately and count toward warning/review burden; they must not improve recall or classification accuracy.

## Benchmark acceptance scenarios

| ID | Given / When / Then |
| --- | --- |
| EVAL-001 | Given a candidate with a fabricated symptom, when the pipeline flags its exact claim as `UNSUPPORTED`, then its error instance is detected; a warning on a different claim is not. |
| EVAL-002 | Given an explicit source contradiction, when a correctly targeted conflicting finding identifies the relevant value/polarity, then it is detected; missing evidence alone does not qualify. |
| EVAL-003 | Given a supported annotated claim, when it is `UNCERTAIN` and routed for correction/review without a valid discrepancy, then it contributes to supported-claim false positives. |
| EVAL-004 | Given an important annotated source fact absent from a candidate, when a matching coverage finding names that fact, then it is a detected omission and the fact is not faithfully covered. |
| EVAL-005 | Given one note with two critical errors and a scenario with both, when only one is detected, then critical-error recall is 1/2 for the note and the scenario fails scenario-level detection. |
| EVAL-006 | Given zero applicable expected facts or zero supported claims, when metrics are calculated, then the corresponding metric is `NOT_APPLICABLE` with a visible zero denominator. |
| EVAL-007 | Given a timeout, malformed output, or interrupted run, when results are aggregated, then its case status and failure category remain visible and it cannot be marked successful. |
| EVAL-008 | Given equivalent candidate notes in a baseline/validated pair, when the comparison runs, then both retain the same candidate content hash and the baseline has no reliability findings. |
| EVAL-009 | Given a candidate mismatch within a purported pair, when the comparison is validated, then the pair is invalid, excluded from paired-effect calculations, and visibly reported. |
| EVAL-010 | Given a source/claim span mismatched to its immutable source version, when fixture validation or live capture runs, then the case/run fails evidence-integrity validation and produces no successful scoring result. |
| EVAL-011 | Given a held-out family or duplicate crossing into development/validation, when the benchmark validator runs, then it rejects the dataset/split selection. |
| EVAL-012 | Given a saved result and a fresh run for the same candidate, when shown in the report, then they have distinct IDs and unambiguous historical/new labels. |
| EVAL-013 | Given a full 100+ scenario benchmark, when it is accepted for a selected split, then required category coverage, annotations, IDs, hashes, provenance, and split-integrity checks pass. |
| EVAL-014 | Given a changed prompt/model/rule/code version, when regression evaluation compares it to a compatible reference, then configuration differences, raw counts, deltas, uncertainty, and `PASS`/`REVIEW_REQUIRED`/`REGRESSION` disposition are persisted. |
| EVAL-015 | Given a completed review workflow with observed human decisions, when final-note quality is reported, then it is distinct from automated detection and tied to the final complete revision. |

## Global constraints and exclusions

The feature shall enforce the project evidence-integrity invariants: exact immutable source-version spans; no candidate note as independent evidence for itself; missing evidence distinct from contradiction; no unsupported correction; stale findings after revision; latest complete-note verification before final approval; preserved historical decisions/revisions; and no approval after verification failure/invalid output. Evaluation may exercise these invariants but must never bypass them.

Excluded: audio/speech processing; multi-resident identification/disambiguation; real patient information; medical diagnosis; treatment recommendation; automated clinical decision-making; EHR integration; regulatory certification; production authentication/access management; mobile apps; microservices/distributed infrastructure; model training/fine-tuning; and independent medical-truth verification.

## Success measures and dependencies

- FR-26–FR-33 are traceable to acceptance scenarios and planned tests; optional extensions are not required for core acceptance.
- The benchmark contains at least 100 accepted synthetic German scenarios and a protected held-out split.
- Held-out critical-error recall is reported against the approved ≥95% target with raw counts and uncertainty; this reports benchmark performance, not clinical safety.
- Every displayed aggregate is traceable to case-level match results and configuration provenance.
- Missing concrete integration ports/configuration keys from upstream implementations are documented as implementation discovery gates in `plan.md`; they must be resolved before implementation, not assumed.
