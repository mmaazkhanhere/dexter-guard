from datetime import datetime, timezone

from human_review.contracts import AuditEvent
from human_review.repository import SQLiteReviewRepository


def test_sqlite_review_repository_initializes_idempotently_and_preserves_audit_order(tmp_path):
    path = tmp_path / "review.sqlite3"
    repo = SQLiteReviewRepository(path)
    repo.append_event(AuditEvent(eventId="event-1", sequence=1, occurredAt=datetime.now(timezone.utc), actorLabel="r", eventType="NOTE_CREATED", noteId="n", noteRevision=1, targetType="NOTE_REVISION", targetId="n:r1", payloadDigest="d"))
    repo2 = SQLiteReviewRepository(path)
    assert [event.event_id for event in repo2.audit("n")] == ["event-1"]
