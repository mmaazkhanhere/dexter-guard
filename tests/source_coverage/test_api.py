from fastapi.testclient import TestClient

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
