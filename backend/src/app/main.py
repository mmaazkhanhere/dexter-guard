"""Composition root for the one-URL frontend/backend application.

The domain packages remain independently testable. This module wires their
existing services together and exposes only the transport aliases needed by
the frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse

from evaluation.adapters import DeterministicFixtureAdapter
from evaluation.api import create_router as create_evaluation_router
from evaluation.benchmark import default_dataset
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner
from human_review.api import create_router as create_review_router
from human_review.contracts import ClaimReverificationRequest
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService
from nursing_notes.repository import InMemoryNoteRepository
from nursing_notes.service import NursingNoteService
from source_ingestion.app import create_app as create_source_app
from source_ingestion.contracts import CreateSourceRequest, SourceDocument
from source_ingestion.service import SourceIngestionService


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
    source_service = SourceIngestionService()
    review_service = ReviewService(repository=InMemoryReviewRepository())
    note_service = ReviewAwareNoteService(
        source_service,
        repository=InMemoryNoteRepository(),
        review_service=review_service,
    )
    app = create_source_app(service=source_service, note_service=note_service)
    app.title = "Dexter Guard Reliability Engine"
    app.version = "UI-INTEGRATION-CONTRACT-v1"
    app.state.source_service = source_service
    app.state.note_service = note_service
    app.state.review_service = review_service

    @app.get("/api/v1/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "database": "ready"}

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

    app.include_router(create_review_router(review_service))

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
        repository=SQLiteEvaluationRepository(":memory:"),
    )
    app.state.evaluation_runner = evaluation_runner
    app.include_router(create_evaluation_router(evaluation_runner))
    return app


app = create_app()

__all__ = ["app", "create_app"]
