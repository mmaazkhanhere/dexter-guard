from __future__ import annotations

from .contracts import EvaluationRun


def build_report(run: EvaluationRun) -> dict[str, object]:
    missed = [
        {"scenarioId": result.scenario_id, "candidateId": result.candidate_id, "caseExecutionId": result.case_execution_id, "matchResults": [match.model_dump(mode="json", by_alias=True) for match in result.match_results if match.disposition.value == "FALSE_NEGATIVE"], "status": result.status.value}
        for result in run.case_results
        if any(match.disposition.value == "FALSE_NEGATIVE" for match in result.match_results)
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
        "missedCriticalCases": missed,
        "diagnosticNote": "Synthetic benchmark measurement only; this report makes no clinical-safety claim.",
        "historicalOrLive": "HISTORICAL_SAVED_RESULT" if run.origin.value == "HISTORICAL_SAVED_RESULT" else "NEWLY_EXECUTED",
    }

