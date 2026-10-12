from datetime import datetime, timezone

from human_review.contracts import AuditEvent
from human_review.repository import SQLiteReviewRepository
from human_review.service import ReviewService


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
