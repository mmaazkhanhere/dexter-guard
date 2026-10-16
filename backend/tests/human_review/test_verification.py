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
    claim_count: int | None = None
    failure_code: str | None = None
    failure_reason: str | None = None


class Ports:
    def __init__(self, status="SUCCEEDED", revision=1, claim_count=1):
        self.status = status
        self.revision = revision
        self.claim_count = claim_count

    def extract(self, note_id, revision):
        return Run("claims-1", self.status, note_id=note_id, note_revision=revision, claim_set_id="claims-1", claim_count=self.claim_count)

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


def test_full_verification_preserves_safe_evidence_provider_failure_code():
    class EvidenceTimeoutPorts(Ports):
        def evidence(self, note_id, revision, claim_set_id):
            return Run(
                "evidence-1", "FAILED", note_id=note_id, note_revision=revision,
                claim_set_id=claim_set_id, failure_code="PROVIDER_TIMEOUT",
                failure_reason="The evidence-verifier provider exceeded its configured timeout.",
            )

    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")
    result = FullNoteVerificationService(service).verify(
        "note-1", expected_revision=1, ports=EvidenceTimeoutPorts(), reviewer_label="r", idempotency_key="timeout",
    )

    assert result.status == "FAILED"
    assert result.failure_code == "PROVIDER_TIMEOUT"
    assert "took too long" in result.failure_message
    evidence = next(item for item in result.component_statuses if item.component == "EVIDENCE_VERIFICATION")
    assert evidence.failure_code == "PROVIDER_TIMEOUT"


def test_empty_claim_set_is_invalid_even_if_every_component_reports_success():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Notiz")

    result = FullNoteVerificationService(service).verify(
        "note-1", expected_revision=1, ports=Ports(claim_count=0), reviewer_label="r", idempotency_key="empty-claims",
    )

    assert result.status == "INVALID"
    assert result.failure_code == "EMPTY_CLAIM_SET_REQUIRES_REVIEW"
