from dataclasses import dataclass

from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService
from human_review.verification import FullNoteVerificationService


@dataclass(frozen=True)
class Run:
    run_id: str
    status: str = "SUCCEEDED"
    source_id: str = "source-1"
    source_version: int = 1
    note_id: str = "note-1"
    note_revision: int = 1
    claim_set_id: str = "claims-1"


class Ports:
    def __init__(self, status="SUCCEEDED", revision=1):
        self.status = status
        self.revision = revision

    def extract(self, note_id, revision):
        return Run("claims-1", self.status, note_id=note_id, note_revision=revision, claim_set_id="claims-1")

    def evidence(self, note_id, revision, claim_set_id):
        return Run("evidence-1", self.status, note_id=note_id, note_revision=self.revision, claim_set_id=claim_set_id)

    def validation(self, note_id, revision, claim_set_id):
        return Run("validation-1", self.status, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)

    def coverage(self, note_id, revision, claim_set_id):
        return Run("coverage-1", self.status, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)


def test_full_verification_requires_all_current_component_runs():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    result = FullNoteVerificationService(service).verify("note-1", expected_revision=1, ports=Ports(), reviewer_label="r", idempotency_key="v1")
    assert result.status == "VALID"
    assert {item.component for item in result.component_statuses} == {"CLAIM_EXTRACTION", "EVIDENCE_VERIFICATION", "DETERMINISTIC_VALIDATION", "SOURCE_COVERAGE"}


def test_source_or_revision_mismatch_is_invalid_not_approval_ready():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    result = FullNoteVerificationService(service).verify("note-1", expected_revision=1, ports=Ports(revision=2), reviewer_label="r", idempotency_key="v1")
    assert result.status == "INVALID"


def test_failed_component_is_terminal_failed_and_blocks_approval():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    result = FullNoteVerificationService(service).verify("note-1", expected_revision=1, ports=Ports(status="FAILED"), reviewer_label="r", idempotency_key="v1")
    assert result.status == "FAILED"
