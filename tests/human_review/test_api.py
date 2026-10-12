from datetime import datetime, timezone

from fastapi.testclient import TestClient

from human_review.api import create_app
from human_review.contracts import ComponentStatus, FullNoteVerification, ReviewFinding, SuggestedCorrection
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService


class _VerificationPorts:
    class _Run:
        def __init__(self, run_id, note_id, revision, claim_set_id="claims-1"):
            self.run_id = run_id
            self.status = "SUCCEEDED"
            self.source_id = "source-1"
            self.source_version = 1
            self.note_id = note_id
            self.note_revision = revision
            self.claim_set_id = claim_set_id

    def extract(self, note_id, revision):
        return self._Run("claims-1", note_id, revision)

    def evidence(self, note_id, revision, claim_set_id):
        return self._Run("evidence-1", note_id, revision, claim_set_id)

    def validation(self, note_id, revision, claim_set_id):
        return self._Run("validation-1", note_id, revision, claim_set_id)

    def coverage(self, note_id, revision, claim_set_id):
        return self._Run("coverage-1", note_id, revision, claim_set_id)


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


def test_api_full_verification_returns_terminal_valid_aggregate():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    client = TestClient(create_app(service, verification_ports=_VerificationPorts()))
    response = client.post("/api/v1/reviews/note-1/full-verifications", json={
        "expectedRevision": 1, "reviewerLabel": "reviewer", "idempotencyKey": "full-1",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "VALID"


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


def test_api_accepts_valid_suggestion_as_a_successor_revision():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    service.add_finding(ReviewFinding(
        reviewFindingId="finding-1", origin="REVIEW_OPERATIONAL", noteId="note-1", noteRevision=1,
        sourceId="source-1", sourceVersion=1, severity="MAJOR", severityPolicyVersion="REVIEW_SEVERITY-v1",
        severityRationale="synthetic", explanation="review", evidence={"availability": "MISSING", "spans": [], "excerpts": []},
        state="OPEN", createdAt=datetime.now(timezone.utc),
    ))
    service.add_suggestion(SuggestedCorrection(
        suggestionId="suggestion-1", findingId="finding-1", noteId="note-1", baseRevision=1,
        replacement="Bericht", targetNoteSpan={"startCodePoint": 0, "endCodePointExclusive": 5, "text": "Notiz"},
        supportStatus="USABLE", supportSpans=({"sourceId": "source-1", "sourceVersion": 1, "start": 0, "end": 5},),
        generatedBy="REVIEWER", createdAt=datetime.now(timezone.utc),
    ))
    client = TestClient(create_app(service))
    response = client.post("/api/v1/reviews/note-1/findings/finding-1/decisions", json={
        "expectedRevision": 1, "kind": "SUGGESTION_ACCEPTED", "suggestionId": "suggestion-1",
        "reviewerLabel": "reviewer", "idempotencyKey": "suggestion-decision-1",
    })
    assert response.status_code == 201
    assert response.json()["successorRevision"] == 2
    assert service.get_note("note-1").content == "Bericht"
