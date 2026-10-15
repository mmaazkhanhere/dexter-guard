from __future__ import annotations

from evaluation.adapters import DeterministicFixtureAdapter, PipelineAdapter, PipelineOutcome
from evaluation.benchmark import default_dataset
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

