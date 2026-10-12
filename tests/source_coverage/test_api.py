from fastapi.testclient import TestClient

from source_ingestion.errors import SourceError

from source_coverage.api import create_app
from tests.source_coverage.test_service import make_service


def test_coverage_endpoint_returns_contract_payload_without_note_or_approval():
    service, payload = make_service()
    response = TestClient(create_app(service)).post("/api/v1/coverage-runs", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCEEDED"
    assert "transcriptText" not in body
    assert "approval" not in body


def test_coverage_endpoint_maps_schema_error_to_422():
    service, _ = make_service()
    response = TestClient(create_app(service)).post("/api/v1/coverage-runs", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "SCHEMA_ERROR"


def test_coverage_endpoint_maps_missing_source_to_404():
    service, payload = make_service()
    service.source_repository = type("MissingSourceRepository", (), {"get": lambda self, source_id, source_version: (_ for _ in ()).throw(SourceError("SOURCE_NOT_FOUND", "missing"))})()
    response = TestClient(create_app(service)).post("/api/v1/coverage-runs", json=payload)
    assert response.status_code == 404
    assert response.json()["code"] == "SOURCE_NOT_FOUND"


def test_coverage_endpoint_maps_unavailable_run_store_to_503():
    service, payload = make_service()
    service.run_repository = type("UnavailableRunRepository", (), {"get_by_idempotency": lambda self, key: (_ for _ in ()).throw(RuntimeError("offline"))})()
    response = TestClient(create_app(service)).post("/api/v1/coverage-runs", json=payload)
    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"


def test_coverage_endpoint_maps_unexpected_matcher_failure_to_500():
    class UnexpectedMatcher:
        def match(self, facts, claims, *, run_id):
            raise TypeError("unexpected")

    service, payload = make_service(matcher=UnexpectedMatcher())
    response = TestClient(create_app(service)).post("/api/v1/coverage-runs", json=payload)
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"


def test_coverage_endpoint_maps_idempotency_conflict_to_409():
    service, payload = make_service()
    client = TestClient(create_app(service))
    assert client.post("/api/v1/coverage-runs", json=payload).status_code == 200
    changed = dict(payload, datasetVersion="synthetic-v2")
    response = client.post("/api/v1/coverage-runs", json=changed)
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"
