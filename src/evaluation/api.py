from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from .contracts import EvaluationRunRequest
from .report import build_report
from .repository import SQLiteEvaluationRepository
from .runner import EvaluationRunner


def create_router(runner: EvaluationRunner, repository: SQLiteEvaluationRepository | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/evaluation-runs", tags=["evaluation"])
    store = repository or runner.repository

    @router.post("", status_code=status.HTTP_201_CREATED)
    def execute(request: EvaluationRunRequest):
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

    @router.get("/{evaluationRunId}/export")
    def export_run(evaluationRunId: str):
        run = store.get_run(evaluationRunId) if store else None
        if run is None:
            raise HTTPException(status_code=404, detail={"code": "EVALUATION_RUN_NOT_FOUND", "message": "evaluation run not found"})
        return Response(content=__import__("json").dumps(build_report(run), ensure_ascii=False), media_type="application/json")

    return router

