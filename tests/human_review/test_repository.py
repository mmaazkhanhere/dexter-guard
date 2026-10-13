from datetime import datetime, timezone
import pytest

from human_review.contracts import AuditEvent
from human_review.repository import SQLiteReviewRepository
from human_review.service import ReviewService
from human_review.approval import ReviewServiceError
from human_review.contracts import ClaimReverificationResponse, NoteDisposition


def test_sqlite_review_repository_initializes_idempotently_and_preserves_audit_order(tmp_path):
    path = tmp_path / "review.sqlite3"
    repo = SQLiteReviewRepository(path)
    repo.append_event(AuditEvent(eventId="event-1", sequence=1, occurredAt=datetime.now(timezone.utc), actorLabel="r", eventType="NOTE_CREATED", noteId="n", noteRevision=1, targetType="NOTE_REVISION", targetId="n:r1", payloadDigest="d"))
    repo2 = SQLiteReviewRepository(path)
    assert [event.event_id for event in repo2.audit("n")] == ["event-1"]


def test_sqlite_review_repository_restart_preserves_note_revisions_and_idempotency(tmp_path):
    path = tmp_path / "review.sqlite3"
    repo = SQLiteReviewRepository(path)
    service = ReviewService(repo)
    service.seed_note("n", "source-1", 1, "Initial")
    service.save_revision("n", expected_revision=1, content="Corrected", reviewer_label="reviewer", idempotency_key="revision-1")
    repo.close()

    restarted = SQLiteReviewRepository(path)
    assert restarted.latest["n"] == 2
    assert restarted.notes[("n", 1)].content == "Initial"
    assert restarted.notes[("n", 2)].content == "Corrected"
    assert restarted.idempotency_digest("save-revision", "revision-1") is not None
    restarted.close()


def test_sqlite_repository_rejects_orphan_review_records(tmp_path):
    repo = SQLiteReviewRepository(tmp_path / "review.sqlite3")
    with pytest.raises(Exception, match="NOTE_NOT_FOUND"):
        repo.persist_claim_feedback(ClaimReverificationResponse(
            reviewVerificationId="claim-feedback-1", noteId="missing", noteRevision=1,
            claimId="claim-1", source={"sourceId": "source-1", "sourceVersion": 1},
            upstreamVerificationRunId="run-1", status="SUCCEEDED", approvalEligible=False,
        ))
    repo.close()


def test_sqlite_repository_preserves_claim_feedback_and_audit_reference_after_restart(tmp_path):
    path = tmp_path / "review.sqlite3"
    repo = SQLiteReviewRepository(path)
    service = ReviewService(repo)
    service.seed_note("n", "source-1", 1, "Synthetisch")
    feedback = service.record_claim_feedback(
        "n", note_revision=1, claim_id="claim-1", reviewer_label="reviewer",
        idempotency_key="claim-1", claim_reverifier=lambda note_id, revision, claim_id: "run-1",
    )
    repo.close()
    restarted = SQLiteReviewRepository(path)
    assert restarted.claim_feedback[feedback.review_verification_id].approval_eligible is False
    assert restarted.audit("n")[-1].event_type == "CLAIM_REVERIFICATION_RECORDED"
    restarted.close()
