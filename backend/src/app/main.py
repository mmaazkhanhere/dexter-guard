"""Composition root for the one-URL frontend/backend application.

The domain packages remain independently testable. This module wires their
existing services together and exposes only the transport aliases needed by
the frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse

from evaluation.adapters import DeterministicFixtureAdapter
from evaluation.api import create_router as create_evaluation_router
from evaluation.benchmark import default_dataset
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner
from .llm_config import generation_adapter_from_environment
from human_review.api import create_router as create_review_router
from human_review.contracts import ClaimReverificationRequest
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService
from nursing_notes.repository import InMemoryNoteRepository
from nursing_notes.service import NursingNoteService
from .postgres import PostgresPersistence, create_postgres_persistence
from source_ingestion.app import create_app as create_source_app
from source_ingestion.contracts import CreateSourceRequest, SourceDocument
from source_ingestion.service import SourceIngestionService
from .workflow import ReliabilityWorkflow


class ReviewAwareNoteService(NursingNoteService):
    """Mirror note identities into the review boundary after persistence."""

    def __init__(self, *args: Any, review_service: ReviewService, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.review_service = review_service

    def _register(self, response: Any) -> Any:
        if response.note_id not in self.review_service.repository.latest:
            self.review_service.seed_note(
                response.note_id,
                response.source_id,
                response.source_version,
                response.content,
            )
        return response

    def generate(self, payload: Any) -> Any:
        return self._register(super().generate(payload))

    def import_note(self, payload: Any) -> Any:
        return self._register(super().import_note(payload))


def _saved_examples(source_service: SourceIngestionService) -> list[dict[str, object]]:
    """Expose immutable synthetic benchmark snapshots as selectable examples."""

    examples: list[dict[str, object]] = []
    dataset = default_dataset()
    for case in dataset.scenarios[:12]:
        source = case.source
        repository = source_service.repository
        if not repository.version_exists(source.source_id, source.source_version):
            repository.create_initial(
                SourceDocument(
                    source_id=source.source_id,
                    source_version=source.source_version,
                    resident_test_id=source.resident_test_id,
                    language=source.language,
                    transcript_text=source.transcript_text,
                    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
            )
        examples.append(
            {
                "exampleId": f"synthetic-example-{case.scenario_id}",
                "title": f"{case.scenario_id}: {case.tags[0]}",
                "sourceId": source.source_id,
                "sourceVersion": source.source_version,
                "kind": "DOCUMENTATION",
                "evaluationRunId": None,
                "syntheticOnly": True,
                "candidateNote": case.candidate_notes[0].note_body,
            }
        )
    return examples


def create_app() -> FastAPI:
    database_url = os.getenv("DATABASE_URL", "").strip()
    persistence: PostgresPersistence | None = None
    if database_url:
        persistence = create_postgres_persistence(database_url)
        source_repository = persistence.source
        note_repository = persistence.notes
        review_repository = persistence.review
        evaluation_repository = persistence.evaluation
    else:
        source_repository = None
        note_repository = InMemoryNoteRepository()
        review_repository = InMemoryReviewRepository()
        evaluation_repository = SQLiteEvaluationRepository(":memory:")

    source_service = SourceIngestionService(repository=source_repository) if source_repository is not None else SourceIngestionService()
    review_service = ReviewService(repository=review_repository)
    note_service = ReviewAwareNoteService(
        source_service,
        repository=note_repository,
        generation_adapter=generation_adapter_from_environment(),
        review_service=review_service,
    )
    workflow = ReliabilityWorkflow(
        source_service=source_service,
        note_service=note_service,
        review_service=review_service,
    )
    app = create_source_app(
        service=source_service,
        note_service=note_service,
        verification_service=workflow.evidence_service,
        deterministic_validation_service=workflow.validation_service,
        coverage_service=workflow.coverage_service,
    )
    app.title = "Dexter Guard Reliability Engine"
    app.version = "UI-INTEGRATION-CONTRACT-v1"
    app.state.source_service = source_service
    app.state.note_service = note_service
    app.state.review_service = review_service
    app.state.workflow = workflow
    app.state.claim_extraction_service = workflow.claim_service
    app.state.evidence_verification_service = workflow.evidence_service
    app.state.deterministic_validation_service = workflow.validation_service
    app.state.source_coverage_service = workflow.coverage_service
    app.state.persistence = persistence

    @app.get("/api/v1/health", tags=["health"])
    def health() -> dict[str, str]:
        database_ready = persistence.check() if persistence is not None else False
        return {"status": "ok" if database_ready else "degraded", "database": "ready" if database_ready else "unavailable"}

    @app.post("/api/v1/sources", response_model=SourceDocument, status_code=status.HTTP_201_CREATED)
    def create_v1_source(payload: CreateSourceRequest) -> SourceDocument:
        return source_service.create_source(payload)

    @app.get("/api/v1/sources/{source_id}/versions/{source_version}", response_model=SourceDocument)
    def get_v1_source(source_id: str, source_version: int) -> SourceDocument:
        return source_service.get_source_version(source_id, source_version)

    @app.get("/api/v1/saved-examples", tags=["examples"])
    def saved_examples() -> list[dict[str, object]]:
        return _saved_examples(source_service)

    def _note_revision(note_id: str, revision: int) -> Any:
        try:
            return note_service.repository.get(note_id, revision).response()
        except Exception as error:
            raise HTTPException(status_code=404, detail={"code": "NOTE_NOT_FOUND", "message": "note revision not found"}) from error

    @app.get("/api/v1/notes/{note_id}/revisions/{revision}")
    def get_note_revision(note_id: str, revision: int) -> Any:
        return _note_revision(note_id, revision)

    @app.get("/api/v1/notes/{noteId}/revisions/{noteRevision}")
    def get_note_revision_contract(noteId: str, noteRevision: int) -> Any:
        return _note_revision(noteId, noteRevision)

    @app.post("/api/v1/claims/extract")
    def extract_claims(payload: dict[str, object]) -> Any:
        note_revision_id = payload.get("noteRevisionId")
        if not isinstance(note_revision_id, str) or not note_revision_id.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"code": "INVALID_REQUEST", "message": "noteRevisionId is required."},
            )
        result = workflow.claim_service.extract_claims(note_revision_id)
        return result.model_dump(mode="json", by_alias=True, exclude_none=True)

    app.include_router(create_review_router(review_service, verification_ports=workflow.ports))

    @app.post("/api/v1/reviews/{note_id}/findings/{finding_id}/claim-reverification")
    def claim_reverification_unavailable(note_id: str, finding_id: str, payload: ClaimReverificationRequest) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"code": "DEPENDENCY_UNAVAILABLE", "message": "Claim reverification is not configured."},
        )

    @app.get("/api/v1/reviews/{note_id}")
    def review_context(note_id: str, revision: int | None = Query(default=None, ge=1)) -> dict[str, object]:
        try:
            note = review_service.get_note(note_id, revision)
            source = source_service.get_source_version(note.source_id, note.source_version)
            return review_service.context(note_id, source.transcript_text, revision)
        except Exception as error:
            raise HTTPException(status_code=404, detail={"code": "NOTE_NOT_FOUND", "message": "review context not found"}) from error

    evaluation_runner = EvaluationRunner(
        dataset=default_dataset(),
        adapter=DeterministicFixtureAdapter(),
        repository=evaluation_repository,
    )
    app.state.evaluation_runner = evaluation_runner
    app.include_router(create_evaluation_router(evaluation_runner))
    return app


app = create_app()

__all__ = ["app", "create_app"]
