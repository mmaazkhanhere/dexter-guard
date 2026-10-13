from __future__ import annotations

from evaluation.adapters import DeterministicFixtureAdapter
from evaluation.benchmark import default_dataset
from evaluation.contracts import EvaluationRunRequest
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner
from evaluation.comparison import compare_regression


def test_held_out_reference_run_reports_critical_recall_gate_and_other_metrics_review_only(tmp_path) -> None:
    dataset = default_dataset()
    run = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")).execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="HELD_OUT", executionMode="SAVED_FIXTURE", idempotencyKey="reference-heldout"))
    recall = next(metric for metric in run.aggregate_metrics if metric.metric_id == "critical-error-recall")
    assert recall.value is not None and recall.value >= 0.95
    assert recall.numerator == recall.denominator
    result = compare_regression({"critical-error-recall": (19, 20), "completeness": (20, 20)}, {"critical-error-recall": (20, 20), "completeness": (19, 20)})
    assert result["disposition"] == "REVIEW_REQUIRED"

