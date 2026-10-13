from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from evidence_verification import VerificationService
from source_ingestion.app import create_app


class SourceRepo:
    def get(self, source_id: str, source_version: int) -> object:
        return SimpleNamespace(
            source_id=source_id,
            source_version=source_version,
            resident_test_id="resident-1",
            transcript_text="Keine starken Schmerzen.",
        )


class ClaimRepo:
    def get(self, extraction_run_id: str) -> object:
        claim = SimpleNamespace(
            id="claim-1",
            note_revision_id="note-1:r1",
            resident_test_id="resident-1",
            claim_text="Keine Schmerzen.",
        )
        return SimpleNamespace(status="SUCCEEDED", extraction_run_id=extraction_run_id, claims=(claim,))


class Provider:
    model_id = "demo-model"
    model_version = "1"
    prompt_version = "verification-v1"
    prompt_hash = "sha256:demo"

    def verify(self, *, claims, source_text, run_id):
        start = source_text.index("Keine")
        return {
            "findings": [{
                "claimId": "claim-1",
                "status": "UNCERTAIN",
                "explanation": "Die Einschränkung auf starke Schmerzen bleibt relevant.",
                "sourceSpans": [{"sourceId": "source-1", "sourceVersion": 1, "start": start, "end": len(source_text) - 1}],
                "discrepancies": ["NEGATION"],
            }]
        }


def make_client() -> TestClient:
    verifier = VerificationService(
        source_repository=SourceRepo(),
        claim_repository=ClaimRepo(),
        verifier=Provider(),
        id_factory=lambda: "run-1",
        correlation_factory=iter(("correlation-1", "trace-1")).__next__,
    )
    return TestClient(create_app(verification_service=verifier))


def payload(key: str = "key-1") -> dict[str, object]:
    return {
        "sourceId": "source-1",
        "sourceVersion": 1,
        "noteId": "note-1",
        "noteRevision": 1,
        "claimSetId": "extract-1",
        "idempotencyKey": key,
        "claims": [{"claimId": "claim-1", "residentTestId": "resident-1"}],
    }


def test_verification_endpoint_returns_terminal_success_and_metadata() -> None:
    response = make_client().post("/api/v1/verification-runs", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCEEDED"
    assert body["findings"][0]["evidenceQuotes"][0]["text"] == "Keine starken Schmerzen"
    assert body["annotationPolicyVersion"] == "EVIDENCE_ANNOTATION-v1"
    assert body["evidenceStatusPolicyVersion"] == "EVIDENCE_STATUS-v1"


def test_verification_endpoint_rejects_malformed_request() -> None:
    response = make_client().post("/api/v1/verification-runs", json={"sourceId": "source-1"})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_verification_endpoint_maps_idempotency_conflict_to_409() -> None:
    client = make_client()
    assert client.post("/api/v1/verification-runs", json=payload()).status_code == 200
    changed = payload()
    changed["sourceVersion"] = 2
    response = client.post("/api/v1/verification-runs", json=changed)
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"

