from datetime import datetime, timezone

from fastapi.testclient import TestClient

from human_review.api import create_app
from human_review.contracts import ComponentStatus, FullNoteVerification
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService


def _verification():
    return {
        "fullVerificationId": "verification-1", "noteId": "note-1", "noteRevision": 1,
        "source": {"sourceId": "source-1", "sourceVersion": 1}, "claimSetId": "claims-1",
        "evidenceRunId": "evidence-1", "deterministicValidationRunId": "validation-1", "coverageRunId": "coverage-1",
        "componentStatuses": [
            {"component": "CLAIM_EXTRACTION", "runId": "claims-1", "status": "SUCCEEDED"},
            {"component": "EVIDENCE_VERIFICATION", "runId": "evidence-1", "status": "SUCCEEDED"},
            {"component": "DETERMINISTIC_VALIDATION", "runId": "validation-1", "status": "SUCCEEDED"},
            {"component": "SOURCE_COVERAGE", "runId": "coverage-1", "status": "SUCCEEDED"},
        ], "status": "VALID", "idempotencyKey": "key-1", "requestDigest": "digest-1",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


def test_api_rejects_direct_approval_without_persisted_full_verification():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    client = TestClient(create_app(service))
    response = client.post("/api/v1/reviews/note-1/approve", json={
        "expectedRevision": 1, "fullVerificationId": "verification-1", "reviewerLabel": "reviewer", "idempotencyKey": "approve-1"
    })
    assert response.status_code == 409
    assert response.json()["code"] == "APPROVAL_PRECONDITION_FAILED"


def test_api_rejection_is_available_without_verification():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    client = TestClient(create_app(service))
    response = client.post("/api/v1/reviews/note-1/reject", json={
        "expectedRevision": 1, "reviewerLabel": "reviewer", "reason": "failed verification", "idempotencyKey": "reject-1"
    })
    assert response.status_code == 200
    assert response.json()["kind"] == "REJECTED"


def test_api_records_finding_decision_without_mutating_upstream_record():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    from human_review.contracts import ReviewFinding
    service.add_finding(ReviewFinding(
        reviewFindingId="finding-1", origin="REVIEW_OPERATIONAL", noteId="note-1", noteRevision=1,
        sourceId="source-1", sourceVersion=1, severity="CRITICAL", severityPolicyVersion="REVIEW_SEVERITY-v1",
        severityRationale="integrity", explanation="missing evidence", evidence={"availability": "MISSING", "spans": [], "excerpts": []},
        state="OPEN", createdAt=datetime.now(timezone.utc),
    ))
    client = TestClient(create_app(service))
    response = client.post("/api/v1/reviews/note-1/findings/finding-1/decisions", json={
        "expectedRevision": 1, "kind": "ACKNOWLEDGED", "reviewerLabel": "reviewer", "idempotencyKey": "decision-1"
    })
    assert response.status_code == 201
    assert service.repository.findings["finding-1"].state == "OPEN"
