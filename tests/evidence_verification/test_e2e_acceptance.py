from __future__ import annotations

import hashlib
from types import SimpleNamespace

from fastapi.testclient import TestClient

from evidence_verification import SQLiteVerificationRepository, VerificationService
from source_ingestion.app import create_app

from .fixtures.spec_004_cases import SPEC_004_CASES


def test_immutable_fixture_flows_through_api_and_persists_exact_replay() -> None:
    case = next(item for item in SPEC_004_CASES if item.case_id == "EV-001")

    class SourceRepository:
        def get(self, source_id: str, source_version: int) -> object:
            assert (source_id, source_version) == (case.case_id, 1)
            return SimpleNamespace(source_id=case.case_id, source_version=1, resident_test_id="resident-1", transcript_text=case.source_text)

    class ClaimRepository:
        def get(self, extraction_run_id: str) -> object:
            return SimpleNamespace(
                status="SUCCEEDED",
                extraction_run_id=extraction_run_id,
                claims=(SimpleNamespace(id="EV-001:claim", note_revision_id="note-1:r1", resident_test_id="resident-1", claim_text=case.claim_text),),
            )

    class Verifier:
        model_id = "spec004-fixture-verifier"
        model_version = "fixture-2026-10"
        prompt_version = "verification-v1"
        prompt_hash = "sha256:spec004-fixture"

        def verify(self, *, claims, source_text: str, run_id: str) -> object:
            start = source_text.index("wirkt ruhig")
            return {"findings": [{"claimId": "EV-001:claim", "status": "SUPPORTED", "explanation": "Fixture acceptance.", "sourceSpans": [{"sourceId": case.case_id, "sourceVersion": 1, "start": start, "end": start + len("wirkt ruhig")}], "discrepancies": []}]}

    source = SourceRepository()
    claims = ClaimRepository()
    note = SimpleNamespace(
        source_id=case.case_id,
        source_version=1,
        source_text_hash=hashlib.sha256(case.source_text.encode("utf-8")).hexdigest(),
    )

    class NoteRepository:
        def get(self, note_id: str, revision: int) -> object:
            assert (note_id, revision) == ("note-1", 1)
            return note

    service = VerificationService(
        source_repository=source,
        note_repository=NoteRepository(),
        claim_repository=claims,
        verifier=Verifier(),
        repository=SQLiteVerificationRepository(":memory:"),
        id_factory=lambda: "e2e-run",
        correlation_factory=iter(("e2e-correlation", "e2e-trace")).__next__,
    )
    client = TestClient(create_app(verification_service=service))
    payload = {
        "sourceId": case.case_id,
        "sourceVersion": 1,
        "noteId": "note-1",
        "noteRevision": 1,
        "claimSetId": "EV-001:claims",
        "idempotencyKey": "EV-001:idempotency",
        "claims": [{"claimId": "EV-001:claim", "residentTestId": "resident-1"}],
    }

    first = client.post("/api/v1/verification-runs", json=payload)
    replay = client.post("/api/v1/verification-runs", json=payload)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["status"] == "SUCCEEDED"
    assert first.json()["findings"][0]["claimId"] == "EV-001:claim"
    assert first.json()["findings"][0]["evidenceQuotes"][0]["text"] == "wirkt ruhig"


def test_immutable_fixture_failure_never_exposes_authoritative_findings() -> None:
    case = next(item for item in SPEC_004_CASES if item.case_id == "EV-012")

    class SourceRepository:
        def get(self, source_id: str, source_version: int) -> object:
            return SimpleNamespace(source_id=case.case_id, source_version=1, resident_test_id="resident-1", transcript_text=case.source_text)

    class ClaimRepository:
        def get(self, extraction_run_id: str) -> object:
            return SimpleNamespace(status="SUCCEEDED", extraction_run_id=extraction_run_id, claims=(SimpleNamespace(id="EV-012:claim", note_revision_id="note-1:r1", resident_test_id="resident-1", claim_text=case.claim_text),))

    class MalformedVerifier:
        def verify(self, *, claims, source_text: str, run_id: str) -> object:
            return {"findings": [{"claimId": "EV-012:claim", "status": "SUPPORTED"}]}

    service = VerificationService(
        source_repository=SourceRepository(),
        claim_repository=ClaimRepository(),
        verifier=MalformedVerifier(),
        id_factory=lambda: "e2e-failure",
        correlation_factory=iter(("failure-correlation", "failure-trace")).__next__,
    )
    body = service.verify({
        "sourceId": case.case_id,
        "sourceVersion": 1,
        "noteId": "note-1",
        "noteRevision": 1,
        "claimSetId": "EV-012:claims",
        "idempotencyKey": "EV-012:idempotency",
        "claims": [{"claimId": "EV-012:claim", "residentTestId": "resident-1"}],
    }).model_dump(by_alias=True, exclude_none=True)

    assert body["status"] == "FAILED_VERIFIER"
    assert body["failure"]["code"] == "MALFORMED_VERIFIER_OUTPUT"
    assert "findings" not in body

