from __future__ import annotations

from fastapi.testclient import TestClient

from source_ingestion.app import create_app

from .test_service import make_service, request


def test_deterministic_validation_endpoint_returns_run_and_no_transcript() -> None:
    response = TestClient(create_app(deterministic_validation_service=make_service())).post(
        "/api/v1/deterministic-validation-runs", json=request()
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rulesetVersion"] == "DVE-RULESET-v1"
    assert body["findings"] == []
    assert "transcriptText" not in body
    assert "approval" not in body


def test_endpoint_maps_schema_missing_claim_ids_to_422() -> None:
    response = TestClient(create_app(deterministic_validation_service=make_service())).post(
        "/api/v1/deterministic-validation-runs", json={"rulesetVersion": "DVE-RULESET-v1"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "SCHEMA_ERROR"


def test_endpoint_maps_unavailable_validation_dependency_to_503() -> None:
    response = TestClient(create_app()).post(
        "/api/v1/deterministic-validation-runs", json=request()
    )
    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"

