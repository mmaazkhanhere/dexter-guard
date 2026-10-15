from __future__ import annotations

from types import SimpleNamespace

import pytest

from evaluation.contracts import FindingMatch, MatchDisposition, ObservedFinding
from evaluation.matching import match_findings
from evaluation.metrics import calculate_metrics, calculate_rate, wilson_interval
from evaluation.runner import _claim_classification_results


def test_matching_requires_actual_target_and_discrepancy_and_does_not_double_count() -> None:
    finding = ObservedFinding(
        findingKey="f1", producer="SPEC_004", upstreamRunId="r1", affectedClaimId="c1",
        affectedSourceFactId=None, primaryStatusOrOutcome="UNSUPPORTED", discrepancyOrRule="FABRICATION",
        conflictingAttributeOrValue=None, sourceSpans=[], requiresCorrectionOrReview=True,
    )
    error = {"errorId": "e1", "candidateId": "cand", "affectedAnnotatedClaimId": "c1", "affectedSourceFactId": None,
             "category": "UNSUPPORTED_FACT", "severity": "CRITICAL", "expectedPrimaryStatus": "UNSUPPORTED",
             "requiredDiscrepancyOrRule": "FABRICATION", "conflictingAttribute": None, "expectedValue": None,
             "sourceEvidenceSpans": [], "applicable": True}
    results = match_findings((finding, finding), (error,))
    assert results[0].disposition is MatchDisposition.MATCHED
    assert results[1].disposition in {MatchDisposition.DUPLICATE, MatchDisposition.UNMATCHED_WARNING}


def test_unnecessary_uncertain_is_a_supported_claim_false_positive_and_wilson_is_defined() -> None:
    assert calculate_rate(1, 10, metric_id="supported-claim-fpr").value == 0.1
    interval = wilson_interval(95, 100)
    assert interval.lower < 0.95 < interval.upper


def test_claim_classification_accuracy_counts_wrong_predictions() -> None:
    metrics = calculate_metrics((), claim_classification_results=(True, False))

    accuracy = next(metric for metric in metrics if metric.metric_id == "claim-classification-accuracy")
    assert accuracy.numerator == 1
    assert accuracy.denominator == 2
    assert accuracy.value == 0.5


@pytest.mark.parametrize(
    ("correct", "expected_value"),
    [(10, 1.0), (6, 0.6), (0, 0.0)],
)
def test_claim_classification_accuracy_reports_prediction_ratio(correct: int, expected_value: float) -> None:
    metrics = calculate_metrics((), claim_classification_results=(True,) * correct + (False,) * (10 - correct))

    accuracy = next(metric for metric in metrics if metric.metric_id == "claim-classification-accuracy")
    assert accuracy.numerator == correct
    assert accuracy.denominator == 10
    assert accuracy.value == expected_value


def test_missing_and_duplicate_predictions_are_incorrect() -> None:
    candidate = SimpleNamespace(
        annotated_claims=(
            SimpleNamespace(annotated_claim_id="claim-1", expected_primary_status=SimpleNamespace(value="SUPPORTED"), scorable=True),
            SimpleNamespace(annotated_claim_id="claim-2", expected_primary_status=SimpleNamespace(value="CONTRADICTED"), scorable=True),
        ),
    )

    missing = _claim_classification_results(
        SimpleNamespace(
            claim_classification_predictions=(("runtime-1", "SUPPORTED"),),
            claim_id_ordinals=(("runtime-1", 1),),
        ),
        candidate,
    )
    duplicate = _claim_classification_results(
        SimpleNamespace(
            claim_classification_predictions=(("runtime-1", "SUPPORTED"), ("runtime-1", "SUPPORTED")),
            claim_id_ordinals=(("runtime-1", 1),),
        ),
        candidate,
    )

    assert missing == (True, False)
    assert duplicate == (False, False)

