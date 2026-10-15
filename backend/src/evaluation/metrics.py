from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from statistics import mean
from dataclasses import dataclass

from .contracts import (
    CaseStatus, CountMetric, DistributionMetric, EvaluationCaseResult, FindingMatch, MatchDisposition,
    MetricState, RateMetric,
)


@dataclass(frozen=True)
class WilsonInterval:
    lower: float
    upper: float


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> WilsonInterval | None:
    if trials <= 0:
        return None
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5)
    return WilsonInterval((centre - margin) / denominator, (centre + margin) / denominator)


def calculate_rate(numerator: int, denominator: int, *, metric_id: str, scorable_count: int | None = None, unscorable_count: int = 0, failed_count: int = 0) -> RateMetric:
    interval = wilson_interval(numerator, denominator)
    return RateMetric(
        metricId=metric_id, metricKind="RATE", state=MetricState.SCORED if denominator else MetricState.NOT_APPLICABLE,
        scorableCount=scorable_count if scorable_count is not None else denominator, unscorableCount=unscorable_count,
        failedCount=failed_count, aggregationMethod="exact-count-ratio", policyVersion="EVALUATION_METRICS-v1",
        numerator=numerator, denominator=denominator, value=numerator / denominator if denominator else None,
        confidenceInterval={"method": "WILSON_95", "level": 0.95, "lower": interval.lower, "upper": interval.upper} if interval else None,
        reason="zero denominator" if denominator == 0 else None,
    )


def _distribution(metric_id: str, values: Iterable[float], *, kind: str, unit: str, currency: str | None = None) -> DistributionMetric:
    data = sorted(float(value) for value in values)
    if not data:
        return DistributionMetric(metricId=metric_id, metricKind=kind, state=MetricState.NOT_APPLICABLE, scorableCount=0, unscorableCount=0, failedCount=0, aggregationMethod="empirical-distribution", policyVersion="EVALUATION_METRICS-v1", observationCount=0, unit=unit, currency=currency, reason="zero observations")
    def percentile(q: float) -> float:
        position = (len(data) - 1) * q
        lower = int(position)
        upper = min(lower + 1, len(data) - 1)
        return data[lower] + (data[upper] - data[lower]) * (position - lower)
    return DistributionMetric(metricId=metric_id, metricKind=kind, state=MetricState.SCORED, scorableCount=len(data), unscorableCount=0, failedCount=0, aggregationMethod="linear-interpolated-percentiles", policyVersion="EVALUATION_METRICS-v1", observationCount=len(data), p50=percentile(.50), p95=percentile(.95), mean=mean(data), unit=unit, currency=currency)


def finding_confusion_counts(case_results: Sequence[EvaluationCaseResult]) -> tuple[int, int, int]:
    """Return strict finding-level TP, FP, and FN counts.

    A target-linked misclassification is both an incorrect prediction and a
    missed exact error, so it contributes to FP and FN.  This keeps the metric
    conservative when a detector identifies the right claim but the wrong rule.
    """
    true_positives = false_positives = false_negatives = 0
    for result in case_results:
        for match in result.match_results:
            if match.disposition is MatchDisposition.MATCHED:
                true_positives += 1
            elif match.disposition in {
                MatchDisposition.UNMATCHED_WARNING,
                MatchDisposition.DUPLICATE,
                MatchDisposition.TARGET_LINKED_MISCLASSIFICATION,
            }:
                false_positives += 1
                if match.disposition is MatchDisposition.TARGET_LINKED_MISCLASSIFICATION:
                    false_negatives += 1
            elif match.disposition is MatchDisposition.FALSE_NEGATIVE:
                false_negatives += 1
    return true_positives, false_positives, false_negatives


def _count_metric(metric_id: str, count: int, unit: str, case_results: Sequence[EvaluationCaseResult], *, failed: int, unscorable: int) -> CountMetric:
    return CountMetric(
        metricId=metric_id,
        metricKind="COUNT_PER_NOTE",
        state=MetricState.SCORED if case_results else MetricState.NOT_APPLICABLE,
        scorableCount=len(case_results),
        unscorableCount=unscorable,
        failedCount=failed,
        aggregationMethod="exact-count-sum",
        policyVersion="EVALUATION_METRICS-v1",
        count=count,
        noteCount=len(case_results),
        valuePerNote=count / len(case_results) if case_results else None,
        unit=unit,
        reason="zero notes" if not case_results else None,
    )


def calculate_metrics(case_results: Sequence[EvaluationCaseResult], *, supported_claims: int = 0, supported_false_positives: int = 0, claim_classification_results: Sequence[bool] = (), expected_facts: int = 0, covered_facts: int = 0, critical_errors: int = 0, detected_critical_errors: int = 0, scenario_critical_total: int = 0, scenario_critical_detected: int = 0) -> tuple[RateMetric | CountMetric | DistributionMetric, ...]:
    failed = sum(result.status in {CaseStatus.FAILED, CaseStatus.INVALID_OUTPUT} for result in case_results)
    unscorable = sum(result.status is CaseStatus.UNSCORABLE for result in case_results)
    true_positives, false_positives, false_negatives = finding_confusion_counts(case_results)
    metrics: list[RateMetric | CountMetric | DistributionMetric] = [
        _count_metric("finding-true-positives", true_positives, "TRUE_POSITIVES", case_results, failed=failed, unscorable=unscorable),
        _count_metric("finding-false-positives", false_positives, "FALSE_POSITIVES", case_results, failed=failed, unscorable=unscorable),
        _count_metric("finding-false-negatives", false_negatives, "FALSE_NEGATIVES", case_results, failed=failed, unscorable=unscorable),
        calculate_rate(true_positives, true_positives + false_positives, metric_id="finding-precision", scorable_count=true_positives + false_positives, unscorable_count=unscorable, failed_count=failed),
        calculate_rate(true_positives, true_positives + false_negatives, metric_id="finding-recall", scorable_count=true_positives + false_negatives, unscorable_count=unscorable, failed_count=failed),
        calculate_rate(2 * true_positives, 2 * true_positives + false_positives + false_negatives, metric_id="finding-f1", scorable_count=2 * true_positives + false_positives + false_negatives, unscorable_count=unscorable, failed_count=failed),
        # Finding-only annotations do not define the population of true
        # negatives, so binary accuracy is intentionally reported as N/A.
        calculate_rate(0, 0, metric_id="finding-accuracy", scorable_count=0, unscorable_count=unscorable, failed_count=failed),
        calculate_rate(detected_critical_errors, critical_errors, metric_id="critical-error-recall", scorable_count=critical_errors, unscorable_count=unscorable, failed_count=failed),
        calculate_rate(supported_false_positives, supported_claims, metric_id="supported-claim-false-positive-rate", scorable_count=supported_claims, unscorable_count=unscorable, failed_count=failed),
        calculate_rate(sum(claim_classification_results), len(claim_classification_results), metric_id="claim-classification-accuracy", scorable_count=len(claim_classification_results), unscorable_count=unscorable, failed_count=failed),
        calculate_rate(covered_facts, expected_facts, metric_id="completeness", scorable_count=expected_facts, unscorable_count=unscorable, failed_count=failed),
        calculate_rate(scenario_critical_detected, scenario_critical_total, metric_id="scenario-level-detection", scorable_count=scenario_critical_total, unscorable_count=unscorable, failed_count=failed),
    ]
    warning_count = sum(
        finding.requires_correction_or_review
        for result in case_results
        for finding in result.observed_findings
    )
    metrics.append(CountMetric(metricId="review-burden-warnings", metricKind="COUNT_PER_NOTE", state=MetricState.SCORED if case_results else MetricState.NOT_APPLICABLE, scorableCount=len(case_results), unscorableCount=unscorable, failedCount=failed, aggregationMethod="sum-per-note", policyVersion="EVALUATION_METRICS-v1", count=warning_count, noteCount=len(case_results), valuePerNote=warning_count / len(case_results) if case_results else None, unit="WARNINGS", reason="zero notes" if not case_results else None))
    review_available = any(result.review_outcome is not None for result in case_results)
    for metric_id, unit, value in (
        ("review-burden-human-decisions", "HUMAN_DECISIONS", sum(result.review_outcome.human_decision_count for result in case_results if result.review_outcome)),
        ("review-burden-correction-actions", "CORRECTION_ACTIONS", sum(result.review_outcome.correction_action_count for result in case_results if result.review_outcome)),
        ("final-note-remaining-errors", "ERRORS", sum(result.review_outcome.remaining_error_count for result in case_results if result.review_outcome)),
        ("final-note-remaining-omissions", "ERRORS", sum(result.review_outcome.remaining_omission_count for result in case_results if result.review_outcome)),
    ):
        metrics.append(CountMetric(metricId=metric_id, metricKind="COUNT_PER_NOTE", state=MetricState.SCORED if review_available else MetricState.UNAVAILABLE if case_results else MetricState.NOT_APPLICABLE, scorableCount=len(case_results), unscorableCount=unscorable, failedCount=failed, aggregationMethod="sum-per-note", policyVersion="EVALUATION_METRICS-v1", count=value, noteCount=len(case_results), valuePerNote=value / len(case_results) if review_available and case_results else None, unit=unit, reason=None if review_available else "human review data unavailable" if case_results else "zero notes"))
    metrics.append(_distribution("verification-latency", (result.latency.end_to_end_milliseconds for result in case_results if result.latency.end_to_end_milliseconds is not None), kind="DURATION_DISTRIBUTION", unit="MILLISECONDS"))
    metrics.append(_distribution("additional-inference-cost", (result.usage_and_cost.estimated_cost for result in case_results if result.usage_and_cost.cost_state == "AVAILABLE" and result.usage_and_cost.estimated_cost is not None), kind="COST_DISTRIBUTION", unit="CURRENCY_PER_NOTE", currency="EUR"))
    return tuple(metrics)

