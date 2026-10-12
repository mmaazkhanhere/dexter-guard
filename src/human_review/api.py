from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .contracts import FullNoteVerification
from .service import ReviewService
from .approval import ReviewServiceError


def _error(error: ReviewServiceError) -> JSONResponse:
    code = str(error)
    status = 409 if code in {"STALE_REVISION", "FINAL_DISPOSITION_IMMUTABLE", "APPROVAL_PRECONDITION_FAILED", "PROVENANCE_CONFLICT"} else 400
    return JSONResponse(status_code=status, content={"code": code, "message": code})


def create_router(service: ReviewService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/reviews")

    @router.post("/{note_id}/revisions", status_code=201)
    def save_revision(note_id: str, payload: dict[str, Any]):
        try:
            note = service.save_revision(note_id, expected_revision=payload["expectedRevision"], content=payload["content"], reviewer_label=payload["reviewerLabel"])
            return {"noteId": note.note_id, "revision": note.revision, "previousRevision": note.revision - 1, "noteStatus": "AWAITING_FULL_VERIFICATION", "auditEventId": service.audit(note_id)[-1].event_id}
        except (ReviewServiceError, KeyError) as error:
            return _error(error if isinstance(error, ReviewServiceError) else ReviewServiceError("INVALID_REQUEST"))

    @router.post("/{note_id}/approve")
    def approve(note_id: str, payload: dict[str, Any]):
        try:
            verification_id = payload["fullVerificationId"]
            verification = service.repository.verifications.get(verification_id)
            if verification is None:
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
            result = service.approve(note_id, expected_revision=payload["expectedRevision"], full_verification=verification, reviewer_label=payload["reviewerLabel"], rationale=payload.get("rationale"))
            return result.model_dump(mode="json", by_alias=True)
        except (ReviewServiceError, KeyError) as error:
            return _error(error if isinstance(error, ReviewServiceError) else ReviewServiceError("INVALID_REQUEST"))

    @router.post("/{note_id}/reject")
    def reject(note_id: str, payload: dict[str, Any]):
        try:
            result = service.reject(note_id, expected_revision=payload["expectedRevision"], reviewer_label=payload["reviewerLabel"], reason=payload["reason"])
            return result.model_dump(mode="json", by_alias=True)
        except (ReviewServiceError, KeyError) as error:
            return _error(error if isinstance(error, ReviewServiceError) else ReviewServiceError("INVALID_REQUEST"))

    @router.get("/{note_id}/audit")
    def audit(note_id: str):
        return {"contractVersion": "REVIEW-AUDIT-CONTRACT-v1", "noteId": note_id, "events": [event.model_dump(mode="json", by_alias=True) for event in service.audit(note_id)]}

    return router


def create_app(service: ReviewService | None = None) -> FastAPI:
    service = service or ReviewService()
    app = FastAPI(title="Dexter Guard Human Review and Audit", version="REVIEW-AUDIT-CONTRACT-v1")
    app.include_router(create_router(service))
    return app
