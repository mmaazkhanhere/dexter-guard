from datetime import datetime, timezone

import pytest

from human_review.approval import ApprovalEligibilityPolicy, ReviewServiceError
from human_review.contracts import (
    ComponentStatus,
    FullNoteVerification,
    ReviewFinding,
    ReviewDecision,
    SuggestedCorrection,
)
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService


def _service() -> ReviewService:
    return ReviewService(InMemoryReviewRepository())


def _finding(*, severity="CRITICAL", revision=1) -> ReviewFinding:
    return ReviewFinding(
        reviewFindingId=f"finding-{revision}",
        origin="REVIEW_OPERATIONAL",
        noteId="note-1",
        noteRevision=revision,
        sourceId="source-1",
        sourceVersion=1,
        severity=severity,
        severityPolicyVersion="REVIEW_SEVERITY-v1",
        severityRationale="deterministic test policy",
        explanation="synthetic review finding",
        evidence={"availability": "MISSING", "spans": [], "excerpts": []},
        state="OPEN",
        createdAt=datetime.now(timezone.utc),
    )


def _valid_verification(revision=1) -> FullNoteVerification:
    statuses = [
        ComponentStatus(component="CLAIM_EXTRACTION", runId="claim-run", status="SUCCEEDED"),
        ComponentStatus(component="EVIDENCE_VERIFICATION", runId="evidence-run", status="SUCCEEDED"),
        ComponentStatus(component="DETERMINISTIC_VALIDATION", runId="validation-run", status="SUCCEEDED"),
        ComponentStatus(component="SOURCE_COVERAGE", runId="coverage-run", status="SUCCEEDED"),
    ]
    return FullNoteVerification(
        fullVerificationId=f"verification-{revision}", noteId="note-1", noteRevision=revision,
        source={"sourceId": "source-1", "sourceVersion": 1}, claimSetId="claim-set",
        evidenceRunId="evidence-run", deterministicValidationRunId="validation-run",
        coverageRunId="coverage-run", componentStatuses=statuses, status="VALID",
        idempotencyKey=f"verify-{revision}", requestDigest="digest", createdAt=datetime.now(timezone.utc),
    )


def test_revision_save_is_append_only_and_stale_writer_does_not_write():
    service = _service()
    service.seed_note("note-1", "source-1", 1, "Initial note")
    saved = service.save_revision("note-1", expected_revision=1, content="Corrected note", reviewer_label="reviewer")
    assert saved.revision == 2
    assert service.get_note("note-1", 1).content == "Initial note"
    with pytest.raises(ReviewServiceError, match="STALE_REVISION"):
        service.save_revision("note-1", expected_revision=1, content="Lost update", reviewer_label="other")
    assert service.get_note("note-1").content == "Corrected note"


def test_critical_finding_acknowledgement_does_not_clear_blocker():
    service = _service()
    service.seed_note("note-1", "source-1", 1, "Initial note")
    service.add_finding(_finding())
    decision = service.record_decision("note-1", "finding-1", expected_revision=1, kind="ACKNOWLEDGED", reviewer_label="r")
    assert decision.outcome == "NO_STATE_CHANGE"
    with pytest.raises(ReviewServiceError, match="APPROVAL_PRECONDITION_FAILED"):
        service.approve("note-1", expected_revision=1, full_verification=_valid_verification(), reviewer_label="r")


def test_approval_requires_latest_valid_full_verification_and_no_critical_open_finding():
    service = _service()
    service.seed_note("note-1", "source-1", 1, "Initial note")
    service.add_finding(_finding(severity="MAJOR"))
    verification = _valid_verification()
    with pytest.raises(ReviewServiceError, match="APPROVAL_PRECONDITION_FAILED"):
        service.approve("note-1", expected_revision=1, full_verification=verification, reviewer_label="r")
    service.persist_verification(verification)
    assert service.approve("note-1", expected_revision=1, full_verification=verification, reviewer_label="r").kind == "APPROVED"


def test_failed_verification_still_allows_rejection_and_audit_is_append_only():
    service = _service()
    service.seed_note("note-1", "source-1", 1, "Initial note")
    disposition = service.reject("note-1", expected_revision=1, reviewer_label="r", reason="verification failed")
    assert disposition.kind == "REJECTED"
    events = service.audit("note-1")
    assert [event.event_type for event in events] == ["NOTE_CREATED", "NOTE_REJECTED"]
    with pytest.raises(ReviewServiceError, match="FINAL_DISPOSITION_IMMUTABLE"):
        service.save_revision("note-1", expected_revision=1, content="reopen", reviewer_label="r")
