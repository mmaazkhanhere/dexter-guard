from fastapi.testclient import TestClient

from human_review.api import create_app
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService


def test_review_context_reads_authoritative_source_and_note_without_client_text():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    client = TestClient(create_app(service, source_reader=lambda source_id, version: "Transcript"))
    response = client.get("/api/v1/reviews/note-1")
    assert response.status_code == 200
    assert response.json()["transcriptText"] == "Transcript"
    assert response.json()["candidateNote"] == "Notiz"


def test_claim_feedback_is_never_approval_eligible():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    client = TestClient(create_app(service, claim_reverifier=lambda note_id, revision, claim_id: "claim-run-1"))
    response = client.post("/api/v1/reviews/note-1/claim-reverification", json={
        "noteRevision": 1, "claimId": "claim-1", "reviewerLabel": "reviewer", "idempotencyKey": "claim-1"
    })
    assert response.status_code == 200
    assert response.json()["approvalEligible"] is False
