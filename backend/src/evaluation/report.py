from __future__ import annotations

from .contracts import EvaluationRun
from collections import Counter


def build_report(run: EvaluationRun) -> dict[str, object]:
    missed = [
        {"scenarioId": result.scenario_id, "candidateId": result.candidate_id, "caseExecutionId": result.case_execution_id, "matchResults": [match.model_dump(mode="json", by_alias=True) for match in result.match_results if match.disposition.value == "FALSE_NEGATIVE"], "status": result.status.value}
        for result in run.case_results
        if any(match.disposition.value == "FALSE_NEGATIVE" for match in result.match_results)
    ]
    dispositions = Counter(match.disposition.value for result in run.case_results for match in result.match_results)
    categories = Counter(failure.code for result in run.case_results if result.failure for failure in (result.failure,))
    incorrect = [
        {
            "scenarioId": result.scenario_id,
            "candidateId": result.candidate_id,
            "caseExecutionId": result.case_execution_id,
            "match": match.model_dump(mode="json", by_alias=True),
        }
        for result in run.case_results
        for match in result.match_results
        if match.disposition.value in {"UNMATCHED_WARNING", "DUPLICATE", "TARGET_LINKED_MISCLASSIFICATION"}
    ]
    return {
        "evaluationRunId": run.evaluation_run_id,
        "origin": run.origin.value,
        "runStatus": run.status.value,
        "scoringState": run.scoring_state,
        "configuration": run.configuration.model_dump(mode="json", by_alias=True),
        "dataset": {"datasetId": run.dataset_id, "datasetVersion": run.dataset_version, "datasetHash": run.dataset_hash, "selectedSplit": run.selected_split.value if run.selected_split else None},
        "metrics": [metric.model_dump(mode="json", by_alias=True) for metric in run.aggregate_metrics],
        "failures": run.failure_summary.model_dump(mode="json", by_alias=True),
        "matchDispositionCounts": dict(sorted(dispositions.items())),
        "failureCategoryCounts": dict(sorted(categories.items())),
        "falsePositiveCaseIds": [result.case_execution_id for result in run.case_results if any(match.disposition.value in {"UNMATCHED_WARNING", "DUPLICATE", "TARGET_LINKED_MISCLASSIFICATION"} for match in result.match_results)],
        "falseNegativeCaseIds": [result.case_execution_id for result in run.case_results if any(match.disposition.value == "FALSE_NEGATIVE" for match in result.match_results)],
        "missedCriticalCases": missed,
        "incorrectDetections": incorrect,
        "diagnosticNote": "Live verifier benchmark measurement; this report makes no clinical-safety claim." if run.configuration.fixture_mode == "LIVE" else "Synthetic fixture benchmark measurement only; this report makes no clinical-safety claim.",
        "historicalOrLive": "HISTORICAL_SAVED_RESULT" if run.origin.value == "HISTORICAL_SAVED_RESULT" else "NEWLY_EXECUTED",
        "evaluationEvidence": "LIVE_MODEL" if run.configuration.fixture_mode == "LIVE" else "SAVED_FIXTURE" if run.configuration.fixture_mode == "SAVED_FIXTURE" else "MOCKED_PROVIDER",
        "interpretation": "Live verifier measurement; interpret with the reported sample size, confidence intervals, provider failures, latency, and cost." if run.configuration.fixture_mode == "LIVE" else "Fixture or mocked-provider measurement; this does not establish live verifier accuracy.",
        "annotationReviewStatus": run.configuration.annotation_review_status,
        "annotationWarning": None if run.configuration.annotation_review_status == "INDEPENDENTLY_REVIEWED" else "Ground-truth annotations are not independently reviewed; do not treat this run as validated model reliability.",
    }

