"""Composition root for the one-URL frontend/backend application.

The domain packages remain independently testable. This module wires their
existing services together and exposes only the transport aliases needed by
the frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse

from evaluation.adapters import DeterministicFixtureAdapter, ReliabilityEngineEvaluationAdapter
from evaluation.api import create_router as create_evaluation_router
from evaluation.benchmark import default_dataset
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner
from evaluation.contracts import EvaluationRunRequest
from .llm_config import evidence_verifier_from_environment, generation_adapter_from_environment
from .demo import DemoStep, FounderDemoScenario
from .observability import workflow_log
from human_review.api import create_router as create_review_router
from human_review.contracts import ClaimReverificationRequest
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService
from nursing_notes.repository import InMemoryNoteRepository
from nursing_notes.service import NursingNoteService
from nursing_notes.contracts import ImportRequest
from nursing_notes.adapters import UnavailableGenerationAdapter
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


_DOCUMENTATION_EXAMPLES = (
    (
        "Guter Schlaf und ausreichendes Trinken",
        "Die Bewohnerin berichtet, in der vergangenen Nacht gut und ohne längere Unterbrechungen geschlafen zu haben. Sie ist am Morgen wach, ansprechbar und orientiert. Im Verlauf des Vormittags trinkt sie selbstständig mehrere Schlucke Wasser; eine genaue Trinkmenge liegt zu diesem Zeitpunkt noch nicht vor.",
    ),
    (
        "Schmerzfreiheit auf Nachfrage",
        "Bei der morgendlichen Befragung verneint die Bewohnerin Schmerzen. Sie beschreibt weder Schmerzen in Ruhe noch Beschwerden bei der Bewegung im Bett. Die Bewohnerin wirkt entspannt und bittet nicht um ein Schmerzmittel.",
    ),
    (
        "Morgendliche Temperaturkontrolle",
        "Bei der morgendlichen Kontrolle wird eine Körpertemperatur von 37,2 °C gemessen. Die Messung erfolgt in Ruhe. Die Bewohnerin wirkt insgesamt stabil und berichtet über kein Kälte- oder Hitzegefühl.",
    ),
    (
        "Dokumentierte Trinkmenge",
        "Bis 10:00 Uhr trinkt die Bewohnerin insgesamt 500 ml Wasser und Tee. Sie nimmt die Getränke selbstständig zu sich und bittet einmal um Unterstützung beim Öffnen des Bechers. Übelkeit oder Erbrechen werden nicht beobachtet.",
    ),
    (
        "Sicherer Transfer ohne Schwindel",
        "Beim Aufstehen vom Bett wird die Bewohnerin begleitet und langsam an die Sitzkante geführt. Sie verneint Schwindel und Kreislaufbeschwerden. Anschließend geht sie mit Unterstützung wenige Schritte bis zum Stuhl und setzt sich sicher hin.",
    ),
    (
        "Husten wird verneint",
        "Die Bewohnerin verneint Husten und Auswurf. Die Atmung wirkt während des Gesprächs ruhig und regelmäßig. Bei der kurzen Mobilisation zeigt sie keine sichtbare Atemnot und kann in vollständigen Sätzen sprechen.",
    ),
    (
        "Mögliche Müdigkeit beobachten",
        "Die Bewohnerin wirkt am Vormittag etwas müde und antwortet mit leichter Verzögerung. Sie gibt an, sich möglicherweise erschöpft zu fühlen. Nach einer kurzen Ruhepause ist sie weiterhin ansprechbar und äußert keinen weiteren Unterstützungsbedarf.",
    ),
    (
        "Übelkeit nach eigener Angabe",
        "Die Bewohnerin berichtet über ein leichtes Übelkeitsgefühl nach dem Frühstück. Sie verneint Erbrechen und kann kleine Schlucke Wasser behalten. Die Beobachtung wird im weiteren Verlauf fortgeführt.",
    ),
    (
        "Blasse Hautbeobachtung",
        "Bei der morgendlichen Pflege wirkt die Haut der Bewohnerin blasser als zuvor. Die Bewohnerin ist wach und ansprechbar. Sie berichtet über keine Schmerzen und keinen Schwindel; die Beobachtung wird an die zuständige Pflegefachkraft weitergegeben.",
    ),
    (
        "Wach und ansprechbar",
        "Die Bewohnerin ist am Vormittag wach, ansprechbar und reagiert passend auf Fragen. Sie kann ihren Namen nennen und äußert den Wunsch, später im Sessel zu sitzen. Die Kommunikation ist ruhig und ohne erkennbare Verständigungsprobleme möglich.",
    ),
    (
        "Unklare Schwindelangabe",
        "Die Bewohnerin berichtet möglicherweise über ein leichtes Schwindelgefühl beim ersten Aufstehen. Sie kann die Stärke nicht genauer einschätzen und verneint einen Sturz. Der Transfer wird zunächst pausiert und nach einer kurzen Sitzpause erneut beurteilt.",
    ),
    (
        "Begleitung zum Tisch",
        "Die Bewohnerin geht mit Unterstützung zum Tisch im Zimmer. Sie setzt die Füße sicher auf und benötigt nur eine kurze verbale Anleitung. Nach dem Hinsetzen bleibt sie stabil sitzen und nimmt dort ihr Frühstück ein.",
    ),
)

_FOUNDER_DEMO_TRANSCRIPT = (
    "Bei der morgendlichen Kontrolle beträgt die Temperatur der Bewohnerin 37,4 Grad Celsius. "
    "Die Bewohnerin verneint Übelkeit."
)
_FOUNDER_DEMO_FLAWED_NOTE = (
    "Bei der morgendlichen Kontrolle beträgt die Temperatur der Bewohnerin 38,4 Grad Celsius. "
    "Die Bewohnerin berichtet über Übelkeit. Eine deutliche Hautrötung wurde beobachtet."
)
_FOUNDER_DEMO_CORRECTED_NOTE = _FOUNDER_DEMO_TRANSCRIPT


def _saved_examples(source_service: SourceIngestionService) -> list[dict[str, object]]:
    """Expose curated, verbose, immutable synthetic examples for documentation."""

    examples: list[dict[str, object]] = []
    source_documents = [
        SourceDocument(
            source_id=f"synthetic-documentation-source-{index:03d}",
            source_version=1,
            resident_test_id=f"synthetic-documentation-resident-{index:03d}",
            language="de-DE",
            transcript_text=transcript,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        for index, (_, transcript) in enumerate(_DOCUMENTATION_EXAMPLES, start=1)
    ]
    source_service.repository.ensure_initial(source_documents)
    for index, (title, _) in enumerate(_DOCUMENTATION_EXAMPLES, start=1):
        source = source_documents[index - 1]
        examples.append(
            {
                "exampleId": f"documentation-example-{index:02d}",
                "title": title,
                "sourceId": source.source_id,
                "sourceVersion": source.source_version,
                "kind": "DOCUMENTATION",
                "evaluationRunId": None,
                "syntheticOnly": True,
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
    evidence_verifier = evidence_verifier_from_environment()
    generation_adapter = generation_adapter_from_environment()
    note_service = ReviewAwareNoteService(
        source_service,
        repository=note_repository,
        generation_adapter=generation_adapter,
        review_service=review_service,
    )
    review_service.attach_note_revision_writer(note_service.create_revision)
    workflow = ReliabilityWorkflow(
        source_service=source_service,
        note_service=note_service,
        review_service=review_service,
        evidence_verifier=evidence_verifier,
    )
    app = create_source_app(
        service=source_service,
        note_service=note_service,
        verification_service=workflow.evidence_service,
        deterministic_validation_service=workflow.validation_service,
        coverage_service=workflow.coverage_service,
    )

    @app.middleware("http")
    async def observe_request(request, call_next):
        """Trace every API request without logging its body or query parameters."""

        request_id = request.headers.get("x-request-id") or f"request-{uuid4()}"
        path = request.url.path
        operation = _operation_for_path(path)
        started = perf_counter()
        workflow_log(operation, "HTTP_REQUEST_STARTED", requestId=request_id, method=request.method, path=path)
        try:
            response = await call_next(request)
        except Exception as error:
            workflow_log(
                operation,
                "HTTP_REQUEST_FAILED",
                outcome="ERROR",
                requestId=request_id,
                method=request.method,
                path=path,
                errorType=type(error).__name__,
                latencyMs=round((perf_counter() - started) * 1000, 2),
            )
            raise
        response.headers["x-request-id"] = request_id
        workflow_log(
            operation,
            "HTTP_REQUEST_COMPLETED",
            outcome="SUCCESS" if response.status_code < 400 else "ERROR",
            requestId=request_id,
            method=request.method,
            path=path,
            statusCode=response.status_code,
            latencyMs=round((perf_counter() - started) * 1000, 2),
        )
        return response
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
    saved_examples_cache: list[dict[str, object]] | None = None
    saved_examples_lock = Lock()

    @app.get("/api/v1/health", tags=["health"])
    def health() -> dict[str, object]:
        database_ready = persistence.check() if persistence is not None else False
        generation_configured = not isinstance(generation_adapter, UnavailableGenerationAdapter)
        generation_model = getattr(generation_adapter, "model_id", None)
        generation_mode = "live" if generation_configured else "unavailable"
        return {
            "status": "ok" if database_ready else "degraded",
            "database": "ready" if database_ready else "unavailable",
            "generationProvider": "UNAVAILABLE" if isinstance(generation_adapter, UnavailableGenerationAdapter) else "LIVE_AI",
            "verificationProvider": "OFFLINE_DEMO" if evidence_verifier is None else "LIVE_AI",
            "generation": {
                "mode": generation_mode,
                "provider": "configured" if generation_configured else None,
                "model": generation_model,
                "configured": generation_configured,
                "available": generation_configured,
                "reason": None if generation_configured else "LLM provider configuration is missing.",
            },
            "verification": {
                "configured": evidence_verifier is not None,
                "available": evidence_verifier is not None,
            },
        }

    @app.post("/api/v1/sources", response_model=SourceDocument, status_code=status.HTTP_201_CREATED)
    def create_v1_source(payload: CreateSourceRequest) -> SourceDocument:
        return source_service.create_source(payload)

    @app.get("/api/v1/sources/{source_id}/versions/{source_version}", response_model=SourceDocument)
    def get_v1_source(source_id: str, source_version: int) -> SourceDocument:
        return source_service.get_source_version(source_id, source_version)

    @app.get("/api/v1/saved-examples", tags=["examples"])
    def saved_examples() -> list[dict[str, object]]:
        nonlocal saved_examples_cache
        if saved_examples_cache is None:
            with saved_examples_lock:
                if saved_examples_cache is None:
                    saved_examples_cache = _saved_examples(source_service)
        return saved_examples_cache

    @app.post("/api/v1/demo-scenarios/founder-walkthrough/start", response_model=FounderDemoScenario, status_code=status.HTTP_201_CREATED, tags=["demo"])
    def start_founder_demo() -> FounderDemoScenario:
        """Create a normal persisted review workflow for the first-time demo.

        The source and imported candidate are deliberately synthetic.  The
        endpoint creates no verification, decision, or approval: visitors must
        perform those human-review steps themselves.
        """
        source = source_service.create_source(
            CreateSourceRequest(
                resident_test_id=f"synthetic-founder-demo-{uuid4().hex[:12]}",
                language="de-DE",
                transcript_text=_FOUNDER_DEMO_TRANSCRIPT,
            )
        )
        note = note_service.import_note(
            ImportRequest(
                sourceId=source.source_id,
                sourceVersion=source.source_version,
                content=_FOUNDER_DEMO_FLAWED_NOTE,
                externalOrigin={"system": "dexter-guard-founder-demo", "externalNoteId": f"founder-walkthrough-{uuid4()}"},
                requestedBy="synthetic-founder-demo",
                facts=(),
            )
        )
        return FounderDemoScenario(
            source=source,
            note=note,
            correctedNote=_FOUNDER_DEMO_CORRECTED_NOTE,
            steps=(
                DemoStep(id="INSPECT", title="Inspect the source", instruction="Compare the original synthetic transcript with the imported candidate note."),
                DemoStep(id="VERIFY", title="Run verification", instruction="Run full verification to reveal the altered measurement, negation error, and source-absent observation."),
                DemoStep(id="CORRECT", title="Correct the note", instruction="Replace the candidate text with the evidence-supported version and save a successor revision."),
                DemoStep(id="REVERIFY", title="Re-verify the new revision", instruction="Run full verification again for the exact saved successor revision."),
                DemoStep(id="APPROVE", title="Approve as a human", instruction="When the corrected revision is eligible, record an explicit human approval."),
            ),
        )

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
        adapter=ReliabilityEngineEvaluationAdapter(evidence_verifier=evidence_verifier),
        repository=evaluation_repository,
    )
    if not evaluation_repository.list_runs():
        fixture_runner = EvaluationRunner(
            dataset=default_dataset(),
            adapter=DeterministicFixtureAdapter(),
            repository=evaluation_repository,
        )
        fixture_dataset = default_dataset()
        fixture_runner.execute(EvaluationRunRequest(
            subjectKind="BENCHMARK",
            datasetId=fixture_dataset.dataset_id,
            datasetVersion=fixture_dataset.dataset_version,
            datasetHash=fixture_dataset.content_hash,
            selectedSplit="HELD_OUT",
            executionMode="SAVED_FIXTURE",
            idempotencyKey="preloaded-heldout-fixture-v1",
        ))
    app.state.evaluation_runner = evaluation_runner
    app.include_router(create_evaluation_router(evaluation_runner, allow_live=os.getenv("EVALUATION_ALLOW_LIVE_API", "false").strip().lower() == "true"))
    return app


def _operation_for_path(path: str) -> str:
    """Classify route paths into a workflow boundary for readable console logs."""

    if path.endswith("/health"):
        return "HEALTH"
    if "/evaluation" in path:
        return "EVALUATION"
    if "/reviews/" in path:
        return "HUMAN_REVIEW"
    if "/coverage" in path:
        return "SOURCE_COVERAGE"
    if "/deterministic-validation" in path:
        return "DETERMINISTIC_VALIDATION"
    if "/verification" in path:
        return "EVIDENCE_VERIFICATION"
    if "/claims/" in path:
        return "CLAIM_EXTRACTION"
    if "/notes/" in path:
        return "NOTE"
    if "/sources" in path or "/source-spans" in path or "/saved-examples" in path:
        return "SOURCE"
    return "REQUEST"


app = create_app()

__all__ = ["app", "create_app"]
