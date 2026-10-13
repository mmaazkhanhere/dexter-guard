"""FastAPI transport adapter for the source coverage service."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from .service import CoverageServiceError, SourceCoverageService


def create_router(service: SourceCoverageService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.post("/coverage-runs")
    def create_coverage_run(payload: dict):
        try:
            result = service.execute(payload)
            return result.model_dump(mode="json", by_alias=True)
        except CoverageServiceError as error:
            if error.code == "SCHEMA_ERROR":
                return JSONResponse(status_code=422, content={"code": error.code, "message": str(error)})
            return JSONResponse(status_code=error.status_code, content={"code": error.code, "message": str(error)})

    return router


def create_app(service: SourceCoverageService) -> FastAPI:
    app = FastAPI(title="Dexter Guard Source Coverage", version="COVERAGE-CONTRACT-v1")
    app.include_router(create_router(service))
    return app
