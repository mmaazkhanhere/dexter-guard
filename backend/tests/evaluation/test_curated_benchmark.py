from __future__ import annotations

import hashlib

import pytest

from evaluation.adapters import DeterministicFixtureAdapter, RealEvaluationAdapter
from evaluation.benchmark import CURATED_REQUIRED_TAGS, curated_held_out_dataset, default_dataset
from evaluation.comparison import compare_paired_cases, paired_metric_report
from evaluation.contracts import DatasetSplit, EvaluationRunRequest
from evaluation.dataset import DatasetValidationError, validate_dataset
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner


def _request(dataset, *, key: str, mode: str) -> EvaluationRunRequest:
    return EvaluationRunRequest(
        subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version,
        datasetHash=dataset.content_hash, selectedSplit="HELD_OUT", executionMode=mode,
        idempotencyKey=key,
    )


def test_regression_fixture_is_preserved_and_curated_corpus_is_varied_held_out_data() -> None:
    regression = default_dataset()
    curated = curated_held_out_dataset()

    assert regression.dataset_version == "008-v1"
    assert len(regression.scenarios) == 100
    assert curated.dataset_version == "008-curated-v1"
    assert len(curated.scenarios) == 30
    assert {case.split.value for case in curated.scenarios} == {"HELD_OUT"}
    assert {tag for case in curated.scenarios for tag in case.tags} >= CURATED_REQUIRED_TAGS
    assert all(case.annotation_provenance.review_status == "PENDING" for case in curated.scenarios)
    assert all(case.source.transcript_text.count(".") >= 2 for case in curated.scenarios)
    assert len({case.source.transcript_text for case in curated.scenarios}) == 30


def test_curated_corpus_is_reproducible_and_validates_its_held_out_profile() -> None:
    first = curated_held_out_dataset()
    second = curated_held_out_dataset()

    assert first.content_hash == second.content_hash
    assert validate_dataset(first).accepted is True


def test_curated_corpus_validator_rejects_development_or_validation_leakage() -> None:
    dataset = curated_held_out_dataset()
    leaked = dataset.scenarios[0].model_copy(update={"split": DatasetSplit.DEVELOPMENT})
    changed = dataset.model_copy(update={"scenarios": (leaked, *dataset.scenarios[1:])})
    changed = changed.model_copy(update={"content_hash": hashlib.sha256(changed.canonical_content().encode()).hexdigest()})

    with pytest.raises(DatasetValidationError, match="held out"):
        validate_dataset(changed)


def test_curated_actual_verifier_run_reports_separate_quality_metrics(tmp_path) -> None:
    regression = default_dataset()
    curated = curated_held_out_dataset()
    repository = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")

    saved_run = EvaluationRunner(
        dataset=regression, adapter=DeterministicFixtureAdapter(), repository=repository,
    ).execute(_request(regression, key="regression-fixture", mode="SAVED_FIXTURE"))
    actual_run = EvaluationRunner(
        dataset=curated, adapter=RealEvaluationAdapter(), repository=repository,
    ).execute(_request(curated, key="curated-actual-verifier", mode="LIVE"))

    metrics = {metric.metric_id: metric for metric in actual_run.aggregate_metrics}
    assert actual_run.dataset_id == curated.dataset_id
    assert actual_run.dataset_hash == curated.content_hash
    assert actual_run.configuration.fixture_mode == "LIVE"
    assert saved_run.dataset_id != actual_run.dataset_id
    assert saved_run.evaluation_run_id != actual_run.evaluation_run_id
    assert {"critical-error-recall", "supported-claim-false-positive-rate", "claim-classification-accuracy"} <= metrics.keys()
    assert metrics["critical-error-recall"].denominator > 0
    assert metrics["supported-claim-false-positive-rate"].denominator > 0
    assert metrics["claim-classification-accuracy"].denominator > 0
    assert any(result.observed_findings for result in actual_run.case_results)
    warnings = metrics["review-burden-warnings"]
    assert warnings.count == sum(
        finding.requires_correction_or_review
        for result in actual_run.case_results
        for finding in result.observed_findings
    )


def test_curated_baseline_vs_validated_report_keeps_raw_metrics_and_configuration(tmp_path) -> None:
    dataset = curated_held_out_dataset()
    repository = SQLiteEvaluationRepository(tmp_path / "paired.sqlite3")
    baseline = EvaluationRunner(
        dataset=dataset, adapter=RealEvaluationAdapter(reliability_enabled=False), repository=repository,
    ).execute(_request(dataset, key="curated-baseline", mode="LIVE"))
    validated = EvaluationRunner(
        dataset=dataset, adapter=RealEvaluationAdapter(), repository=repository,
    ).execute(_request(dataset, key="curated-validated", mode="LIVE"))

    comparison = compare_paired_cases(
        baseline.evaluation_run_id, validated.evaluation_run_id,
        baseline.case_results, validated.case_results,
    )
    report = paired_metric_report(baseline, validated)
    assert comparison.status.value == "VALID"
    assert len(comparison.pair_results) == 30
    assert set(report["validated"]["metrics"]) >= {
        "finding-true-positives", "finding-false-negatives", "finding-false-positives",
        "critical-error-recall", "supported-claim-false-positive-rate",
        "claim-classification-accuracy", "review-burden-warnings", "verification-latency",
    }
    assert report["baseline"]["metrics"]["finding-true-positives"]["count"] == 0
    assert report["validated"]["configuration"]["fixtureMode"] == "LIVE"
    assert report["validated"]["datasetVersion"] == "008-curated-v1"
    assert report["validated"]["metrics"]["critical-error-recall"]["confidenceInterval"]["method"] == "WILSON_95"
