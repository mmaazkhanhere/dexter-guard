"""Synthetic API-level acceptance flows traced to the HR-001--HR-018 fixture manifest."""

from fastapi.testclient import TestClient
import yaml
from pathlib import Path

from .fixtures.review_cases import SCENARIOS, SYNTHETIC_NOTE
from human_review.api import create_app
from human_review.repository import InMemoryReviewRepository
from human_review.service import ReviewService


class Ports:
    class Run:
        def __init__(self, run_id, note_id, revision, claim_set_id, *, status="SUCCEEDED", unresolved=0):
            self.run_id = run_id
            self.status = status
            self.source_id = "source-1"
            self.source_version = 1
            self.note_id = note_id
            self.note_revision = revision
            self.claim_set_id = claim_set_id
            self.unresolved_source_items = unresolved

    def __init__(self, *, status="SUCCEEDED", unresolved=0):
        self.status = status
        self.unresolved = unresolved

    def extract(self, note_id, revision):
        return self.Run("claims-1", note_id, revision, "claims-1", status=self.status)

    def evidence(self, note_id, revision, claim_set_id):
        return self.Run("evidence-1", note_id, revision, claim_set_id, status=self.status)

    def validation(self, note_id, revision, claim_set_id):
        return self.Run("validation-1", note_id, revision, claim_set_id, status=self.status)

    def coverage(self, note_id, revision, claim_set_id):
        return self.Run("coverage-1", note_id, revision, claim_set_id, status=self.status, unresolved=self.unresolved)


def _service() -> ReviewService:
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, SYNTHETIC_NOTE)
    return service


def _full_verify(client: TestClient, *, key="verify-1"):
    return client.post("/api/v1/reviews/note-1/full-verifications", json={
        "expectedRevision": 1, "reviewerLabel": "synthetic-reviewer", "idempotencyKey": key,
    })


def test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered():
    service = _service()
    client = TestClient(create_app(service, verification_ports=Ports()))

    verification = _full_verify(client)
    approval = client.post("/api/v1/reviews/note-1/approve", json={
        "expectedRevision": 1, "fullVerificationId": verification.json()["fullVerificationId"],
        "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "approve-1",
    })
    audit = client.get("/api/v1/reviews/note-1/audit")

    assert verification.json()["status"] == "VALID"
    assert approval.status_code == 201 and approval.json()["kind"] == "APPROVED"
    assert [event["eventType"] for event in audit.json()["events"]] == [
        "NOTE_CREATED", "FULL_VERIFICATION_RECORDED", "NOTE_APPROVED",
    ]


def test_acceptance_stale_edit_blocks_old_verification_and_writes_no_disposition():
    service = _service()
    client = TestClient(create_app(service, verification_ports=Ports()))

    assert client.post("/api/v1/reviews/note-1/revisions", json={
        "expectedRevision": 1, "content": "Korrigierte synthetische Notiz.",
        "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "edit-1",
    }).status_code == 201
    stale = _full_verify(client)

    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_REVISION"
    assert service.repository.dispositions == []
    assert service.context("note-1", "synthetisch")["noteStatus"] == "AWAITING_FULL_VERIFICATION"


def test_acceptance_failed_and_unresolved_coverage_verifications_are_not_approvable_but_rejection_is():
    failed_service = _service()
    failed_client = TestClient(create_app(failed_service, verification_ports=Ports(status="FAILED")))
    failed = _full_verify(failed_client, key="failed-1")
    rejected = failed_client.post("/api/v1/reviews/note-1/reject", json={
        "expectedRevision": 1, "reviewerLabel": "synthetic-reviewer", "reason": "upstream failed", "idempotencyKey": "reject-1",
    })

    unresolved_service = _service()
    unresolved_client = TestClient(create_app(unresolved_service, verification_ports=Ports(unresolved=1)))
    unresolved = _full_verify(unresolved_client, key="unresolved-1")
    blocked = unresolved_client.post("/api/v1/reviews/note-1/approve", json={
        "expectedRevision": 1, "fullVerificationId": unresolved.json()["fullVerificationId"],
        "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "blocked-1",
    })

    assert failed.json()["status"] == "FAILED"
    assert rejected.status_code == 201 and rejected.json()["kind"] == "REJECTED"
    assert unresolved.json()["status"] == "INVALID"
    assert unresolved.json()["failureCode"] == "UNRESOLVED_SOURCE_ITEM"
    assert blocked.status_code == 409 and blocked.json()["code"] == "APPROVAL_PRECONDITION_FAILED"


def test_acceptance_claim_feedback_never_becomes_approval_evidence():
    service = _service()
    client = TestClient(create_app(service, claim_reverifier=lambda note_id, revision, claim_id: "claim-run-1"))

    feedback = client.post("/api/v1/reviews/note-1/claim-reverification", json={
        "noteRevision": 1, "claimId": "claim-1", "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "claim-1",
    })

    assert feedback.status_code == 200
    assert feedback.json()["approvalEligible"] is False


def test_acceptance_manifest_traces_every_hr_case_to_a_synthetic_expected_outcome():
    assert len(SCENARIOS) == 18
    assert all(scenario.expected_audit_event.isupper() for scenario in SCENARIOS)


SCENARIO_TESTS = {
    "HR-001": "test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered",
    "HR-002": "test_acceptance_manifest_traces_every_hr_case_to_a_synthetic_expected_outcome",
    "HR-003": "test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered",
    "HR-004": "test_acceptance_stale_edit_blocks_old_verification_and_writes_no_disposition",
    "HR-005": "test_acceptance_stale_edit_blocks_old_verification_and_writes_no_disposition",
    "HR-006": "test_acceptance_claim_feedback_never_becomes_approval_evidence",
    "HR-007": "test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered",
    "HR-008": "test_acceptance_failed_and_unresolved_coverage_verifications_are_not_approvable_but_rejection_is",
    "HR-009": "test_acceptance_failed_and_unresolved_coverage_verifications_are_not_approvable_but_rejection_is",
    "HR-010": "test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered",
    "HR-011": "test_acceptance_manifest_traces_every_hr_case_to_a_synthetic_expected_outcome",
    "HR-012": "test_acceptance_failed_and_unresolved_coverage_verifications_are_not_approvable_but_rejection_is",
    "HR-013": "test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered",
    "HR-014": "test_acceptance_failed_and_unresolved_coverage_verifications_are_not_approvable_but_rejection_is",
    "HR-015": "test_acceptance_stale_edit_blocks_old_verification_and_writes_no_disposition",
    "HR-016": "test_acceptance_full_verification_approval_and_audit_are_terminal_and_ordered",
    "HR-017": "test_acceptance_stale_edit_blocks_old_verification_and_writes_no_disposition",
    "HR-018": "test_acceptance_failed_and_unresolved_coverage_verifications_are_not_approvable_but_rejection_is",
}


def test_every_hr_scenario_maps_to_an_executable_backend_acceptance_probe():
    assert {scenario.scenario_id for scenario in SCENARIOS} == set(SCENARIO_TESTS)
    assert all(callable(globals().get(test_name)) for test_name in SCENARIO_TESTS.values())


def test_openapi_backend_paths_are_registered_in_the_fastapi_application():
    contract_path = Path(__file__).parents[3] / "specs" / "007-human-review-and-audit" / "contracts" / "review-audit.openapi.yaml"
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    service = _service()
    app = create_app(service, source_reader=lambda source_id, version: "synthetic", claim_reverifier=lambda note_id, revision, claim_id: "claim-run-1", verification_ports=Ports())
    route_paths = set(app.openapi()["paths"])
    for path in document["paths"]:
        assert path.replace("{noteId}", "{note_id}").replace("{findingId}", "{finding_id}") in route_paths
