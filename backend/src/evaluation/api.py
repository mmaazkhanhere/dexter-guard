from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from .contracts import EvaluationRunRequest
from .report import build_report
from .repository import SQLiteEvaluationRepository
from .runner import EvaluationRunner


def create_router(runner: EvaluationRunner, repository: SQLiteEvaluationRepository | None = None, *, allow_live: bool = False) -> APIRouter:
    router = APIRouter(prefix="/api/v1/evaluation-runs", tags=["evaluation"])
    store = repository or runner.repository

    @router.post("", status_code=status.HTTP_201_CREATED)
    def execute(request: EvaluationRunRequest):
        if request.execution_mode == "LIVE" and not allow_live:
            raise HTTPException(status_code=403, detail={"code": "LIVE_EVALUATION_DISABLED", "message": "Live benchmark execution is disabled on the public API; use the controlled evaluation CLI."})
        return runner.execute(request).model_dump(mode="json", by_alias=True)

    @router.get("")
    def list_runs():
        if store is None:
            return []
        return [build_report(run) for run in store.list_runs()]

    @router.get("/{evaluationRunId}")
    def get_run(evaluationRunId: str):
        run = store.get_run(evaluationRunId) if store else None
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "EVALUATION_RUN_NOT_FOUND", "message": "evaluation run not found"})
        return run.model_dump(mode="json", by_alias=True)

    @router.get("/{evaluationRunId}/cases/{caseExecutionId}")
    def get_case(evaluationRunId: str, caseExecutionId: str):
        run = store.get_run(evaluationRunId) if store else None
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "EVALUATION_RUN_NOT_FOUND", "message": "evaluation run not found"})
        result = next((item for item in run.case_results if item.case_execution_id == caseExecutionId), None)
        if result is None:
            raise HTTPException(status_code=404, detail={"code": "EVALUATION_CASE_NOT_FOUND", "message": "evaluation case not found"})
        case = next((item for item in runner.dataset.scenarios if item.scenario_id == result.scenario_id), None)
        candidate = next((item for item in case.candidate_notes if item.candidate_id == result.candidate_id), None) if case else None
        if case is None or candidate is None:
            raise HTTPException(status_code=409, detail={"code": "EVALUATION_CASE_DATA_UNAVAILABLE", "message": "immutable benchmark case data is unavailable"})
        expected = [error.model_dump(mode="json", by_alias=True) for error in candidate.error_instances]
        actual = [finding.model_dump(mode="json", by_alias=True) for finding in result.observed_findings]
        disagreements = []
        for match in result.match_results:
            disposition = match.disposition.value
            disposition_label = {
                "MATCHED": "True positive",
                "FALSE_NEGATIVE": "False negative",
                "UNMATCHED_WARNING": "False positive",
                "DUPLICATE": "Duplicate finding",
                "TARGET_LINKED_MISCLASSIFICATION": "Classification mismatch",
            }.get(disposition, disposition.replace("_", " ").title())
            explanation = {
                "MATCHED": "The observed finding matches the expected target, classification, discrepancy, and evidence span.",
                "FALSE_NEGATIVE": "The expected error has no valid observed finding.",
                "UNMATCHED_WARNING": "The verifier produced a warning without a matching expected error.",
                "DUPLICATE": "The verifier produced another finding for an already-consumed target.",
                "TARGET_LINKED_MISCLASSIFICATION": "The correct target was identified, but its classification or discrepancy did not match.",
            }.get(disposition, "The result could not be classified by the evaluation matching policy.")
            disagreements.append({"errorId": match.error_id, "findingKey": match.finding_key, "disposition": disposition, "dispositionLabel": disposition_label, "reasonCode": match.reason_code, "explanation": explanation})
        return {
            "evaluationRunId": evaluationRunId,
            "caseExecutionId": caseExecutionId,
            "scenarioId": case.scenario_id,
            "benchmark": {"datasetId": run.dataset_id, "datasetVersion": run.dataset_version, "datasetHash": run.dataset_hash, "selectedSplit": run.selected_split},
            "status": result.status.value,
            "source": case.source.model_dump(mode="json", by_alias=True),
            "candidate": candidate.model_dump(mode="json", by_alias=True, exclude={"annotatedClaims", "errorInstances"}),
            "expectedFindings": expected,
            "actualFindings": actual,
            "disagreements": disagreements,
            "latency": result.latency.model_dump(mode="json", by_alias=True),
            "usageAndCost": result.usage_and_cost.model_dump(mode="json", by_alias=True),
            "failure": result.failure.model_dump(mode="json", by_alias=True) if result.failure else None,
            "configuration": run.configuration.model_dump(mode="json", by_alias=True),
        }

    @router.get("/{evaluationRunId}/export")
    def export_run(evaluationRunId: str):
        run = store.get_run(evaluationRunId) if store else None
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "EVALUATION_RUN_NOT_FOUND", "message": "evaluation run not found"})
        return Response(content=__import__("json").dumps(build_report(run), ensure_ascii=False), media_type="application/json")

    return router

