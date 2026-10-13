from fastapi.testclient import TestClient

from app.main import create_app


def test_composed_app_exposes_safe_health_and_synthetic_examples() -> None:
    client = TestClient(create_app())

    health = client.get("/api/v1/health")
    examples = client.get("/api/v1/saved-examples")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "ready"}
    assert examples.status_code == 200
    assert examples.json()
    assert all(item["syntheticOnly"] is True for item in examples.json())


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


def test_unconfigured_verification_fails_closed() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/verification-runs", json={})

    assert response.status_code == 503
    assert response.json()["code"] == "VERIFIER_UNAVAILABLE"
