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
    assert health.json() == {
        "status": "degraded",
        "database": "unavailable",
        "generationProvider": "UNAVAILABLE",
        "verificationProvider": "OFFLINE_DEMO",
        "generation": {
            "mode": "unavailable",
            "provider": None,
            "model": None,
            "configured": False,
            "available": False,
            "reason": "LLM provider configuration is missing.",
        },
        "verification": {"configured": False, "available": False},
    }
    assert examples.status_code == 200
    assert examples.json()
    assert all(item["syntheticOnly"] is True for item in examples.json())
    assert all(not item["title"].lower().startswith("scenario-") for item in examples.json())
    assert all(len(client.get(f"/api/v1/sources/{item['sourceId']}/versions/{item['sourceVersion']}").json()["transcript_text"]) > 160 for item in examples.json())
    assert cached_examples.json() == examples.json()
    assert app.state.source_service.repository.count() == len(examples.json())
    version_exists.assert_not_called()


def test_founder_demo_creates_a_normal_synthetic_source_and_flawed_imported_note() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/demo-scenarios/founder-walkthrough/start")

    assert response.status_code == 201
    body = response.json()
    assert body["scenarioId"] == "founder-walkthrough-v1"
    assert body["syntheticOnly"] is True
    assert body["source"]["resident_test_id"].startswith("synthetic-founder-demo-")
    assert body["note"]["origin"] == "IMPORTED"
    assert body["note"]["sourceId"] == body["source"]["source_id"]
    assert body["note"]["content"] != body["correctedNote"]
    assert [step["id"] for step in body["steps"]] == ["INSPECT", "VERIFY", "CORRECT", "REVERIFY", "APPROVE"]


def test_founder_demo_completes_only_after_correction_reverification_and_human_approval() -> None:
    client = TestClient(create_app())
    demo = client.post("/api/v1/demo-scenarios/founder-walkthrough/start").json()
    note_id = demo["note"]["noteId"]

    initial = client.post(f"/api/v1/reviews/{note_id}/full-verifications", json={"expectedRevision": 1, "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "demo-initial"})
    assert initial.status_code == 200
    initial_context = client.get(f"/api/v1/reviews/{note_id}?revision=1").json()
    assert initial_context["approvalEligible"] is False
    initial_statuses = {finding["upstreamStatus"] for finding in initial_context["findings"]}
    assert "CONTRADICTED" in initial_statuses
    assert "UNSUPPORTED" in initial_statuses

    saved = client.post(f"/api/v1/reviews/{note_id}/revisions", json={"expectedRevision": 1, "content": demo["correctedNote"], "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "demo-correction"})
    assert saved.status_code == 201
    assert saved.json()["revision"] == 2

    verified = client.post(f"/api/v1/reviews/{note_id}/full-verifications", json={"expectedRevision": 2, "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "demo-reverify"})
    assert verified.status_code == 200
    corrected_context = client.get(f"/api/v1/reviews/{note_id}?revision=2").json()
    assert corrected_context["approvalEligible"] is True

    approval = client.post(f"/api/v1/reviews/{note_id}/approve", json={"expectedRevision": 2, "fullVerificationId": verified.json()["fullVerificationId"], "reviewerLabel": "synthetic-reviewer", "idempotencyKey": "demo-approve"})
    assert approval.status_code == 201
    assert approval.json()["kind"] == "APPROVED"


def test_health_reports_loaded_generation_configuration_without_exposing_credentials() -> None:
    with patch.dict(
        "os.environ",
        {"LLM_API_KEY": "synthetic-secret", "LLM_MODEL": "synthetic-model", "LLM_BASE_URL": "https://llm.example.test/v1"},
        clear=False,
    ):
        health = TestClient(create_app()).get("/api/v1/health")

    assert health.status_code == 200
    assert health.json()["generation"] == {
        "mode": "live",
        "provider": "configured",
        "model": "synthetic-model",
        "configured": True,
        "available": True,
        "reason": None,
    }
    assert "synthetic-secret" not in health.text


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
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["evaluationEvidence"] == "SAVED_FIXTURE"
    assert runs[0]["dataset"]["selectedSplit"] == "HELD_OUT"
