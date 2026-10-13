from __future__ import annotations

from evaluation.comparison import compare_paired_cases, compare_regression
from evaluation.contracts import CaseStatus, EvaluationCaseResult, LatencyBreakdown, UsageAndCost


def _case(case_id: str, note_hash: str, *, findings=()) -> EvaluationCaseResult:
    return EvaluationCaseResult(
        caseExecutionId=f"exec-{case_id}", scenarioId=case_id, candidateId=f"candidate-{case_id}",
        sourceId=f"source-{case_id}", sourceVersion=1, sourceTextHash="a" * 64, noteId=f"note-{case_id}",
        noteRevision=1, noteBodyHash=note_hash, status=CaseStatus.SUCCEEDED, stageRuns=(), observedFindings=findings,
        matchResults=(), completenessResults=(), reviewOutcome=None, latency=LatencyBreakdown(endToEndMilliseconds=10.0),
        usageAndCost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"), failure=None,
    )


def test_paired_comparison_requires_same_candidate_and_clean_baseline() -> None:
    baseline = _case("1", "b" * 64)
    validated = _case("1", "b" * 64)
    comparison = compare_paired_cases("baseline", "validated", (baseline,), (validated,), review_data_kind="SIMULATED", simulation_policy_version="sim-v1")
    assert comparison.status.value == "SIMULATED"
    assert comparison.pair_results[0]["status"] == "VALID"
    invalid = compare_paired_cases("baseline", "validated", (_case("1", "a" * 64, findings=()),), (_case("1", "b" * 64),))
    assert invalid.status.value == "INVALID_PAIR"
    assert invalid.pair_results[0]["status"] == "INVALID_PAIR"


def test_regression_does_not_invent_unapproved_thresholds() -> None:
    result = compare_regression({"critical-error-recall": (95, 100), "completeness": (90, 100)}, {"critical-error-recall": (96, 100), "completeness": (80, 100)})
    assert result["disposition"] == "REVIEW_REQUIRED"
    assert result["deltas"]["completeness"] == -0.1

