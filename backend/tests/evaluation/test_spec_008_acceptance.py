from __future__ import annotations

from evaluation.adapters import DeterministicFixtureAdapter
from evaluation.benchmark import default_dataset
from evaluation.contracts import EvidenceStatus, MatchDisposition, ObservedFinding
from evaluation.dataset import validate_dataset
from evaluation.matching import match_findings
from evaluation.metrics import calculate_rate
from evaluation.runner import EvaluationRunner
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.contracts import EvaluationRunRequest


def test_eval_001_exact_fabrication_target_is_required() -> None:
    dataset = default_dataset()
    case = next(case for case in dataset.scenarios if "UNSUPPORTED_FACT" in case.tags)
    error = case.candidate_notes[0].error_instances[0]
    finding = ObservedFinding(findingKey="exact", producer="SPEC_004", upstreamRunId="r", affectedClaimId=error.affected_annotated_claim_id, affectedSourceFactId=None, primaryStatusOrOutcome="UNSUPPORTED", discrepancyOrRule=error.required_discrepancy_or_rule, conflictingAttributeOrValue=None, sourceSpans=error.source_evidence_spans, requiresCorrectionOrReview=True)
    assert match_findings((finding,), (error,))[0].disposition is MatchDisposition.MATCHED


def test_eval_002_to_005_matching_and_metrics_are_not_percentage_only() -> None:
    dataset = default_dataset()
    assert any("EXPLICIT_CONTRADICTION" in case.tags for case in dataset.scenarios)
    assert any("IMPORTANT_OMISSION" in case.tags for case in dataset.scenarios)
    metric = calculate_rate(1, 2, metric_id="critical-error-recall")
    assert metric.numerator == 1 and metric.denominator == 2 and metric.confidence_interval is not None


def test_eval_006_zero_denominator_is_not_applicable() -> None:
    metric = calculate_rate(0, 0, metric_id="completeness")
    assert metric.state.value == "NOT_APPLICABLE" and metric.value is None


def test_eval_010_to_013_dataset_is_immutable_split_protected_and_synthetic_only() -> None:
    dataset = default_dataset()
    assert validate_dataset(dataset).accepted
    assert all(case.source.language == "de-DE" and case.source.resident_test_id.startswith("synthetic-") for case in dataset.scenarios)


def test_eval_014_and_015_produce_traceable_run_and_distinct_review_boundary(tmp_path) -> None:
    dataset = default_dataset()
    run = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")).execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="HELD_OUT", executionMode="MOCKED_PROVIDER", idempotencyKey="acceptance"))
    assert run.configuration.matching_policy_version == "EVALUATION_MATCHING-v1"
    assert run.aggregate_metrics
    assert all(result.note_body_hash and result.source_text_hash for result in run.case_results)
    recall = next(metric for metric in run.aggregate_metrics if metric.metric_id == "critical-error-recall")
    assert recall.value is not None
    assert next(metric for metric in run.aggregate_metrics if metric.metric_id == "final-note-remaining-errors").state.value == "UNAVAILABLE"
    assert "clinical" not in " ".join(metric.metric_id for metric in run.aggregate_metrics).lower()

