from __future__ import annotations

from evaluation.contracts import FindingMatch, MatchDisposition, ObservedFinding
from evaluation.matching import match_findings
from evaluation.metrics import calculate_rate, wilson_interval


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

