from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import uuid4

from .contracts import ComparisonStatus, EvaluationCaseResult, EvaluationRun, ReviewDataKind, RunComparison


def compare_paired_cases(
    baseline_run_id: str, validated_run_id: str, baseline_cases: Sequence[EvaluationCaseResult],
    validated_cases: Sequence[EvaluationCaseResult], *, review_data_kind: str = "UNAVAILABLE",
    simulation_policy_version: str | None = None, task_digest: str | None = None,
) -> RunComparison:
    """Compare identical fixed candidates; baseline receives no reliability findings."""
    validated_by_key = {(case.scenario_id, case.candidate_id): case for case in validated_cases}
    pairs: list[dict[str, object]] = []
    all_valid = True
    for baseline in baseline_cases:
        key = (baseline.scenario_id, baseline.candidate_id)
        validated = validated_by_key.get(key)
        reason: str | None = None
        if validated is None:
            reason = "MISSING_VALIDATED_CASE"
        elif baseline.note_body_hash != validated.note_body_hash:
            reason = "CANDIDATE_BODY_HASH_MISMATCH"
        elif baseline.source_text_hash != validated.source_text_hash:
            reason = "SOURCE_HASH_MISMATCH"
        elif baseline.observed_findings:
            reason = "BASELINE_CONTAINS_RELIABILITY_FINDINGS"
        if reason:
            all_valid = False
        pairs.append({
            "scenarioId": baseline.scenario_id, "candidateId": baseline.candidate_id,
            "candidateBodyHash": baseline.note_body_hash,
            "baselineCaseExecutionId": baseline.case_execution_id,
            "validatedCaseExecutionId": validated.case_execution_id if validated else "missing",
            "status": "VALID" if reason is None else "INVALID_PAIR", "invalidReason": reason,
        })
    status = ComparisonStatus.VALID if all_valid else ComparisonStatus.INVALID_PAIR
    if review_data_kind == "SIMULATED" and all_valid:
        status = ComparisonStatus.SIMULATED
    return RunComparison(
        comparisonId=f"comparison-{uuid4().hex}", status=status, baselineRunId=baseline_run_id,
        validatedRunId=validated_run_id, pairResults=tuple(pairs), reviewDataKind=ReviewDataKind(review_data_kind),
        simulationPolicyVersion=simulation_policy_version, aggregateDeltas=(),
    )


def compare_regression(
    reference_metrics: Mapping[str, tuple[int, int]], current_metrics: Mapping[str, tuple[int, int]], *, critical_target: float = 0.95,
) -> dict[str, object]:
    """Return raw counts and a conservative disposition; only recall has an approved gate."""
    deltas: dict[str, float | None] = {}
    raw: dict[str, dict[str, int]] = {}
    for metric_id in sorted(set(reference_metrics) | set(current_metrics)):
        ref_num, ref_den = reference_metrics.get(metric_id, (0, 0))
        cur_num, cur_den = current_metrics.get(metric_id, (0, 0))
        ref_value = ref_num / ref_den if ref_den else None
        cur_value = cur_num / cur_den if cur_den else None
        deltas[metric_id] = round(cur_value - ref_value, 12) if cur_value is not None and ref_value is not None else None
        raw[metric_id] = {"referenceNumerator": ref_num, "referenceDenominator": ref_den, "currentNumerator": cur_num, "currentDenominator": cur_den}
    recall = current_metrics.get("critical-error-recall", (0, 0))
    recall_value = recall[0] / recall[1] if recall[1] else None
    if recall_value is not None and recall_value < critical_target:
        disposition = "REGRESSION"
    elif any(metric != "critical-error-recall" and delta not in (None, 0.0) for metric, delta in deltas.items()):
        disposition = "REVIEW_REQUIRED"
    else:
        disposition = "PASS"
    return {"disposition": disposition, "deltas": deltas, "raw": raw, "criticalTarget": critical_target, "uncertainty": "Wilson intervals are persisted on MetricResult; no unapproved threshold is inferred."}


def paired_metric_report(baseline: EvaluationRun, validated: EvaluationRun) -> dict[str, object]:
    """Return an auditable raw-count comparison without inferring improvement."""
    metric_ids = (
        "finding-true-positives", "finding-false-negatives", "finding-false-positives",
        "critical-error-recall", "supported-claim-false-positive-rate",
        "claim-classification-accuracy", "review-burden-warnings", "verification-latency",
    )

    def selected(run: EvaluationRun) -> dict[str, object]:
        by_id = {metric.metric_id: metric for metric in run.aggregate_metrics}
        return {
            metric_id: by_id[metric_id].model_dump(by_alias=True, exclude_none=False)
            for metric_id in metric_ids
            if metric_id in by_id
        }

    return {
        "comparison": "BASELINE_VS_VALIDATED",
        "interpretation": "Automated finding comparison only; no final-note or caregiver outcome is inferred.",
        "baseline": {
            "evaluationRunId": baseline.evaluation_run_id,
            "datasetId": baseline.dataset_id,
            "datasetVersion": baseline.dataset_version,
            "adapter": "ReliabilityEngineEvaluationAdapter(reliability_enabled=false)",
            "verifier": None,
            "configuration": baseline.configuration.model_dump(by_alias=True, exclude_none=False),
            "metrics": selected(baseline),
        },
        "validated": {
            "evaluationRunId": validated.evaluation_run_id,
            "datasetId": validated.dataset_id,
            "datasetVersion": validated.dataset_version,
            "adapter": "ReliabilityEngineEvaluationAdapter(reliability_enabled=true)",
            "verifier": validated.configuration.model_dump(by_alias=True, exclude_none=False).get("modelId"),
            "configuration": validated.configuration.model_dump(by_alias=True, exclude_none=False),
            "metrics": selected(validated),
        },
    }

