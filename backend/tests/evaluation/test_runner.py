from __future__ import annotations

from evaluation.adapters import DeterministicFixtureAdapter, PipelineAdapter, PipelineOutcome
from evaluation.benchmark import curated_held_out_dataset, default_dataset
from evaluation.contracts import EvaluationFailure, EvaluationRunRequest, ObservedFinding, RunStatus, StageRunReference, UsageAndCost
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner


def test_headless_runner_scores_selected_split_and_records_real_metrics(tmp_path) -> None:
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=repo)
    run = runner.execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="HELD_OUT", executionMode="MOCKED_PROVIDER", idempotencyKey="heldout-1"))
    assert run.status is RunStatus.SUCCEEDED
    assert len(run.case_results) == 20
    recall = next(metric for metric in run.aggregate_metrics if metric.metric_id == "critical-error-recall")
    assert recall.denominator > 0
    classification_accuracy = next(metric for metric in run.aggregate_metrics if metric.metric_id == "claim-classification-accuracy")
    assert classification_accuracy.state.value == "NOT_APPLICABLE"
    assert classification_accuracy.denominator == 0
    assert run.selected_split.value == "HELD_OUT"
    assert repo.get_run(run.evaluation_run_id) == run


def test_repeated_deterministic_dataset_runs_reproduce_matches_counts_and_metrics(tmp_path) -> None:
    """Replay reproducibility excludes wall-clock timing and generated run IDs."""
    dataset = default_dataset()
    runner = EvaluationRunner(
        dataset=dataset,
        adapter=DeterministicFixtureAdapter(),
        repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3"),
    )

    def execute(key: str):
        return runner.execute(EvaluationRunRequest(
            subjectKind="BENCHMARK",
            datasetId=dataset.dataset_id,
            datasetVersion=dataset.dataset_version,
            datasetHash=dataset.content_hash,
            selectedSplit="HELD_OUT",
            executionMode="MOCKED_PROVIDER",
            idempotencyKey=key,
        ))

    first = execute("reproducibility-1")
    second = execute("reproducibility-2")

    def stable_projection(run):
        cases = []
        for result in run.case_results:
            cases.append({
                "scenarioId": result.scenario_id,
                "candidateId": result.candidate_id,
                "status": result.status.value,
                "matches": sorted((match.error_id, match.finding_key, match.disposition.value, match.reason_code) for match in result.match_results),
                "findings": sorted((finding.finding_key, finding.affected_claim_id, finding.affected_source_fact_id, finding.primary_status_or_outcome) for finding in result.observed_findings),
                "coverage": sorted((item.source_fact_id, str(item.status), item.faithfully_covered) for item in result.completeness_results),
                "failure": result.failure.code if result.failure else None,
            })
        metrics = []
        for metric in run.aggregate_metrics:
            if metric.metric_id == "verification-latency":
                continue
            metrics.append(metric.model_dump(mode="json", by_alias=True))
        return {"status": run.status.value, "cases": sorted(cases, key=lambda item: (item["scenarioId"], item["candidateId"])), "metrics": sorted(metrics, key=lambda item: item["metricId"]), "failures": run.failure_summary.model_dump(mode="json", by_alias=True)}

    assert stable_projection(first) == stable_projection(second)
    assert first.evaluation_run_id != second.evaluation_run_id
    assert first.case_results[0].latency.end_to_end_milliseconds is not None
    assert second.case_results[0].latency.end_to_end_milliseconds is not None


def test_claim_classification_accuracy_uses_actual_verifier_predictions(tmp_path) -> None:
    class AlwaysSupportedAdapter(PipelineAdapter):
        def evaluate(self, case, candidate):
            return PipelineOutcome(
                findings=(ObservedFinding(
                    findingKey="prediction-1", producer="SPEC_004", upstreamRunId="verifier-run",
                    affectedClaimId="runtime-claim-1", affectedSourceFactId=None,
                    primaryStatusOrOutcome="SUPPORTED", discrepancyOrRule=None,
                    conflictingAttributeOrValue=None, sourceSpans=(), requiresCorrectionOrReview=False,
                ),),
                stage_runs=(StageRunReference(stage="EVIDENCE_VERIFICATION", upstreamRunId="verifier-run", status="SUCCEEDED"),),
                latency_ms=1.0,
                usage_and_cost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"),
                claim_id_ordinals=(("runtime-claim-1", 1),),
                claim_classification_predictions=(("runtime-claim-1", "SUPPORTED"),),
            )

    dataset = default_dataset()
    runner = EvaluationRunner(dataset=dataset, adapter=AlwaysSupportedAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3"))
    run = runner.execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="VALIDATION", executionMode="MOCKED_PROVIDER", idempotencyKey="classification-accuracy-1"))

    accuracy = next(metric for metric in run.aggregate_metrics if metric.metric_id == "claim-classification-accuracy")
    assert all(result.status.value == "SUCCEEDED" for result in run.case_results)
    assert 0 < accuracy.numerator < accuracy.denominator
    assert accuracy.value < 1


def test_live_evaluation_without_predictions_is_not_a_successful_accuracy_score(tmp_path) -> None:
    class NoPredictionAdapter(PipelineAdapter):
        def evaluate(self, case, candidate):
            return PipelineOutcome(
                findings=(),
                stage_runs=(StageRunReference(stage="EVIDENCE_VERIFICATION", upstreamRunId="verifier-run", status="SUCCEEDED"),),
                latency_ms=1.0,
                usage_and_cost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"),
            )

    dataset = default_dataset()
    runner = EvaluationRunner(dataset=dataset, adapter=NoPredictionAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3"))
    run = runner.execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="VALIDATION", executionMode="LIVE", idempotencyKey="classification-no-predictions-1"))

    accuracy = next(metric for metric in run.aggregate_metrics if metric.metric_id == "claim-classification-accuracy")
    assert run.status is RunStatus.SUCCEEDED
    assert accuracy.state.value == "NOT_APPLICABLE"
    assert accuracy.numerator == 0
    assert accuracy.denominator == 0
    assert accuracy.value is None


def test_runner_does_not_score_invalid_dataset_or_silently_use_all_splits(tmp_path) -> None:
    dataset = default_dataset()
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3"))
    bad = EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash="f" * 64, selectedSplit="HELD_OUT", executionMode="MOCKED_PROVIDER", idempotencyKey="bad-1")
    run = runner.execute(bad)
    assert run.status is RunStatus.INVALID_DATASET
    assert not run.case_results


def test_demo_tracking_is_reference_only_and_not_benchmark_evidence(tmp_path) -> None:
    dataset = default_dataset()
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3"))
    request = EvaluationRunRequest(subjectKind="SYNTHETIC_DEMO", executionMode="LIVE", idempotencyKey="demo-1", sourceId="source-1", sourceVersion=1, noteId="note-1", noteRevision=1, upstreamRunIds=("generation-1", "verification-1"), syntheticDataAttestation="synthetic-only")
    run = runner.execute(request)
    assert run.scoring_state == "DEMONSTRATION_ONLY"
    assert run.demo_reference is not None
    assert run.dataset_id is None


def test_idempotent_replay_returns_original_terminal_run_and_failures_remain_visible(tmp_path) -> None:
    class FailingAdapter(PipelineAdapter):
        def evaluate(self, case, candidate):
            return PipelineOutcome(findings=(), stage_runs=(StageRunReference(stage="CLAIM_EXTRACTION", upstreamRunId="r", status="FAILED"),), latency_ms=3.0, usage_and_cost=UsageAndCost(retryCount=1, costState="UNAVAILABLE"), failure=EvaluationFailure(code="PROVIDER_TIMEOUT", stage="CLAIM_EXTRACTION", retryable=True, message="synthetic timeout"))
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")
    runner = EvaluationRunner(dataset=dataset, adapter=FailingAdapter(), repository=repo)
    request = EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="VALIDATION", executionMode="MOCKED_PROVIDER", idempotencyKey="replay-1")
    first = runner.execute(request)
    second = runner.execute(request)
    assert first.evaluation_run_id == second.evaluation_run_id
    assert first.status is RunStatus.PARTIALLY_FAILED
    assert first.failure_summary.failure_codes == ("PROVIDER_TIMEOUT",)


def test_adapter_exception_records_each_ground_truth_error_as_a_false_negative(tmp_path) -> None:
    class RaisingAdapter(PipelineAdapter):
        def evaluate(self, case, candidate):
            raise RuntimeError("synthetic adapter failure")

    dataset = curated_held_out_dataset()
    run = EvaluationRunner(
        dataset=dataset, adapter=RaisingAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3"),
    ).execute(EvaluationRunRequest(
        subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version,
        datasetHash=dataset.content_hash, selectedSplit="HELD_OUT", executionMode="LIVE", idempotencyKey="exception-fn",
    ))

    false_negatives = next(item for item in run.aggregate_metrics if item.metric_id == "finding-false-negatives")
    expected_errors = sum(len(case.candidate_notes[0].error_instances) for case in dataset.scenarios)
    assert false_negatives.count == expected_errors
    assert all(result.match_results or not case.candidate_notes[0].error_instances for case, result in zip(dataset.scenarios, run.case_results))

