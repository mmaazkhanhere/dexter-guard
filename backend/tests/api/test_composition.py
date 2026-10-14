from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


def test_composed_app_exposes_safe_health_and_synthetic_examples() -> None:
    app = create_app()
    client = TestClient(app)
    repository = app.state.source_service.repository

    health = client.get("/api/v1/health")
    with patch.object(repository, "version_exists", wraps=repository.version_exists) as version_exists:
        examples = client.get("/api/v1/saved-examples")
        cached_examples = client.get("/api/v1/saved-examples")

    assert health.status_code == 200
    assert health.json() == {"status": "degraded", "database": "unavailable"}
    assert examples.status_code == 200
    assert examples.json()
    assert all(item["syntheticOnly"] is True for item in examples.json())
    assert all(not item["title"].lower().startswith("scenario-") for item in examples.json())
    assert all(len(client.get(f"/api/v1/sources/{item['sourceId']}/versions/{item['sourceVersion']}").json()["transcript_text"]) > 160 for item in examples.json())
    assert cached_examples.json() == examples.json()
    assert app.state.source_service.repository.count() == len(examples.json())
    version_exists.assert_not_called()


def test_composed_app_preserves_source_and_note_routes() -> None:
    client = TestClient(create_app())

    source = client.post(
        "/api/v1/sources",
        json={
            "resident_test_id": "synthetic-resident-composition",
            "language": "de-DE",
            "transcript_text": "Die Bewohnerin berichtet über guten Schlaf.",
        },
    )

    assert source.status_code == 201
    body = source.json()
    retrieved = client.get(f"/sources/{body['source_id']}/versions/{body['source_version']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["transcript_text"] == body["transcript_text"]


def test_verification_rejects_malformed_request_after_workflow_wiring() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/verification-runs", json={})

    assert response.status_code == 400


def test_composed_app_runs_the_complete_review_workflow() -> None:
    client = TestClient(create_app())
    source = client.post(
        "/api/v1/sources",
        json={
            "resident_test_id": "synthetic-resident-workflow",
            "language": "de-DE",
            "transcript_text": "Die Bewohnerin berichtet keine Schmerzen. Temperatur 37,2 °C.",
        },
    ).json()
    note = client.post(
        "/api/v1/notes/import",
        json={
            "sourceId": source["source_id"],
            "sourceVersion": source["source_version"],
            "content": source["transcript_text"],
            "externalOrigin": {"system": "synthetic-test", "externalNoteId": "workflow-1"},
            "requestedBy": "synthetic-reviewer",
            "facts": [],
        },
    ).json()

    verification = client.post(
        f"/api/v1/reviews/{note['noteId']}/full-verifications",
        json={"expectedRevision": 1, "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "workflow-1"},
    )

    assert verification.status_code == 200
    body = verification.json()
    assert body["status"] == "VALID"
    assert {item["component"] for item in body["componentStatuses"]} == {
        "CLAIM_EXTRACTION",
        "EVIDENCE_VERIFICATION",
        "DETERMINISTIC_VALIDATION",
        "SOURCE_COVERAGE",
    }


def test_composed_app_exposes_evaluation_run_collection() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/evaluation-runs")

    assert response.status_code == 200
    assert response.json() == []
