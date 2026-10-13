from __future__ import annotations

from fastapi import APIRouter, FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .contracts import ApproveRequest, ClaimReverificationRequest, FindingDecisionRequest, FullVerificationRequest, RejectRequest, SaveRevisionRequest
from .service import ReviewService
from .approval import ReviewServiceError
from .verification import FullNoteVerificationService


def _error(error: ReviewServiceError) -> JSONResponse:
    code = str(error)
    status = 503 if code == "DEPENDENCY_UNAVAILABLE" else (404 if code in {"NOTE_NOT_FOUND", "FINDING_NOT_FOUND", "SUGGESTION_NOT_FOUND"} else (409 if code in {"STALE_REVISION", "FINAL_DISPOSITION_IMMUTABLE", "APPROVAL_PRECONDITION_FAILED", "PROVENANCE_CONFLICT", "IDEMPOTENCY_KEY_CONFLICT", "SUGGESTION_TARGET_MISMATCH"} else 400))
    return JSONResponse(status_code=status, content={"code": code, "message": code})


def create_router(service: ReviewService, *, verification_ports=None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/reviews")

    @router.post("/{note_id}/revisions", status_code=201)
    def save_revision(note_id: str, payload: SaveRevisionRequest):
        try:
            note = service.save_revision(note_id, expected_revision=payload.expected_revision, content=payload.content, reviewer_label=payload.reviewer_label, idempotency_key=payload.idempotency_key)
            return {"noteId": note.note_id, "revision": note.revision, "previousRevision": note.revision - 1, "noteStatus": "AWAITING_FULL_VERIFICATION", "auditEventId": service.audit(note_id)[-1].event_id}
        except ReviewServiceError as error:
            return _error(error)

    @router.post("/{note_id}/approve", status_code=201)
    def approve(note_id: str, payload: ApproveRequest):
        try:
            verification_id = payload.full_verification_id
            verification = service.repository.verifications.get(verification_id)
            if verification is None:
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
            result = service.approve(note_id, expected_revision=payload.expected_revision, full_verification=verification, reviewer_label=payload.reviewer_label, rationale=payload.rationale, idempotency_key=payload.idempotency_key)
            return result.model_dump(mode="json", by_alias=True)
        except ReviewServiceError as error:
            return _error(error)

    @router.post("/{note_id}/findings/{finding_id}/decisions", status_code=201)
    def record_decision(note_id: str, finding_id: str, payload: FindingDecisionRequest):
        try:
            result = service.record_decision(note_id, finding_id, expected_revision=payload.expected_revision, kind=payload.kind, reviewer_label=payload.reviewer_label, rationale=payload.rationale, suggestion_id=payload.suggestion_id, idempotency_key=payload.idempotency_key)
            return result.model_dump(mode="json", by_alias=True)
        except ReviewServiceError as error:
            return _error(error)

    @router.post("/{note_id}/reject", status_code=201)
    def reject(note_id: str, payload: RejectRequest):
        try:
            result = service.reject(note_id, expected_revision=payload.expected_revision, reviewer_label=payload.reviewer_label, reason=payload.reason, idempotency_key=payload.idempotency_key)
            return result.model_dump(mode="json", by_alias=True)
        except ReviewServiceError as error:
            return _error(error)

    @router.post("/{note_id}/full-verifications")
    def full_verification(note_id: str, payload: FullVerificationRequest):
        try:
            if verification_ports is None:
                raise ReviewServiceError("DEPENDENCY_UNAVAILABLE")
            result = FullNoteVerificationService(service).verify(note_id, expected_revision=payload.expected_revision, ports=verification_ports, reviewer_label=payload.reviewer_label, idempotency_key=payload.idempotency_key)
            return result.model_dump(mode="json", by_alias=True)
        except (ReviewServiceError, RuntimeError, ValueError) as error:
            return _error(error if isinstance(error, ReviewServiceError) else ReviewServiceError(str(error)))

    @router.get("/{note_id}/suggestions")
    def suggestions(note_id: str, revision: int | None = Query(default=None, ge=1)):
        try:
            service.get_note(note_id, revision)
            selected_revision = revision or service.repository.latest[note_id]
            return {"noteId": note_id, "revision": selected_revision, "suggestions": [item.model_dump(mode="json", by_alias=True) for item in service.repository.suggestions.values() if item.note_id == note_id and item.base_revision == selected_revision]}
        except ReviewServiceError as error:
            return _error(error)

    @router.get("/{note_id}/audit")
    def audit(note_id: str):
        try:
            service.get_note(note_id)
            return {"contractVersion": "REVIEW-AUDIT-CONTRACT-v1", "noteId": note_id, "events": [event.model_dump(mode="json", by_alias=True) for event in service.audit(note_id)]}
        except ReviewServiceError as error:
            return _error(error)

    return router


def create_app(service: ReviewService | None = None, *, source_reader=None, claim_reverifier=None, verification_ports=None) -> FastAPI:
    service = service or ReviewService()
    app = FastAPI(title="Dexter Guard Human Review and Audit", version="REVIEW-AUDIT-CONTRACT-v1")
    app.include_router(create_router(service, verification_ports=verification_ports))
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        return JSONResponse(status_code=422, content={"code": "VALIDATION_ERROR", "message": "request does not satisfy the versioned review contract"})

    if source_reader is not None:
        @app.get("/api/v1/reviews/{note_id}")
        def review_context(note_id: str, revision: int | None = Query(default=None, ge=1)):
            try:
                note = service.get_note(note_id)
                selected = service.get_note(note_id, revision)
                return service.context(note_id, source_reader(selected.source_id, selected.source_version), revision)
            except ReviewServiceError as error:
                return _error(error)
    else:
        @app.get("/api/v1/reviews/{note_id}")
        def review_context_unavailable(note_id: str):
            return _error(ReviewServiceError("DEPENDENCY_UNAVAILABLE"))

    if claim_reverifier is not None:
        @app.post("/api/v1/reviews/{note_id}/findings/{finding_id}/claim-reverification")
        def claim_reverification(note_id: str, finding_id: str, payload: ClaimReverificationRequest):
            try:
                note = service.get_note(note_id)
                finding = service.repository.findings.get(finding_id)
                if finding is None or finding.note_id != note_id or finding.claim_id != payload.claim_id:
                    raise ReviewServiceError("FINDING_NOT_FOUND")
                if note.revision != payload.note_revision or finding.note_revision != payload.note_revision:
                    raise ReviewServiceError("STALE_REVISION")
                result = service.record_claim_feedback(note_id, note_revision=payload.note_revision, claim_id=payload.claim_id, reviewer_label=payload.reviewer_label, idempotency_key=payload.idempotency_key, claim_reverifier=claim_reverifier)
                return result.model_dump(mode="json", by_alias=True)
            except (ReviewServiceError, KeyError) as error:
                return _error(error if isinstance(error, ReviewServiceError) else ReviewServiceError("INVALID_REQUEST"))

        # Compatibility alias for the original local PoC route. New clients should use
        # the finding-scoped contract above so the claim identity is checked server-side.
        @app.post("/api/v1/reviews/{note_id}/claim-reverification")
        def claim_reverification_legacy(note_id: str, payload: ClaimReverificationRequest):
            try:
                note = service.get_note(note_id)
                if note.revision != payload.note_revision:
                    raise ReviewServiceError("STALE_REVISION")
                result = service.record_claim_feedback(note_id, note_revision=payload.note_revision, claim_id=payload.claim_id, reviewer_label=payload.reviewer_label, idempotency_key=payload.idempotency_key, claim_reverifier=claim_reverifier)
                return result.model_dump(mode="json", by_alias=True)
            except ReviewServiceError as error:
                return _error(error)
    else:
        @app.post("/api/v1/reviews/{note_id}/findings/{finding_id}/claim-reverification")
        def claim_reverification_unavailable(note_id: str, finding_id: str, payload: ClaimReverificationRequest):
            return _error(ReviewServiceError("DEPENDENCY_UNAVAILABLE"))
    return app
