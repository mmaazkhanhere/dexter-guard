from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from evaluation.adapters import DeterministicFixtureAdapter
from evaluation.api import create_router
from evaluation.benchmark import default_dataset
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.report import build_report
from evaluation.runner import EvaluationRunner


def test_synchronous_api_lists_gets_and_exports_saved_runs(tmp_path) -> None:
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=repo)
    app = FastAPI()
    app.include_router(create_router(runner, repo))
    client = TestClient(app)
    response = client.post("/api/v1/evaluation-runs", json={"subjectKind": "BENCHMARK", "datasetId": dataset.dataset_id, "datasetVersion": dataset.dataset_version, "datasetHash": dataset.content_hash, "selectedSplit": "VALIDATION", "executionMode": "MOCKED_PROVIDER", "idempotencyKey": "api-1"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["origin"] == "NEWLY_EXECUTED"
    run_id = payload["evaluationRunId"]
    assert client.get(f"/api/v1/evaluation-runs/{run_id}").status_code == 200
    assert client.get(f"/api/v1/evaluation-runs/{run_id}/export").json()["evaluationRunId"] == run_id
    assert len(client.get("/api/v1/evaluation-runs").json()) == 1
    report = build_report(repo.get_run(run_id))
    assert report["evaluationEvidence"] == "MOCKED_PROVIDER"
    assert report["annotationReviewStatus"] == "INDEPENDENTLY_REVIEWED"
    assert report["annotationWarning"] is None


def test_public_evaluation_api_rejects_live_execution_by_default(tmp_path) -> None:
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=repo)
    app = FastAPI()
    app.include_router(create_router(runner, repo))
    client = TestClient(app)

    response = client.post("/api/v1/evaluation-runs", json={"subjectKind": "BENCHMARK", "datasetId": dataset.dataset_id, "datasetVersion": dataset.dataset_version, "datasetHash": dataset.content_hash, "selectedSplit": "HELD_OUT", "executionMode": "LIVE", "idempotencyKey": "public-live-1"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "LIVE_EVALUATION_DISABLED"


def test_case_inspection_returns_source_note_findings_and_explanations(tmp_path) -> None:
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=repo)
    app = FastAPI()
    app.include_router(create_router(runner, repo))
    client = TestClient(app)
    created = client.post("/api/v1/evaluation-runs", json={"subjectKind": "BENCHMARK", "datasetId": dataset.dataset_id, "datasetVersion": dataset.dataset_version, "datasetHash": dataset.content_hash, "selectedSplit": "HELD_OUT", "executionMode": "SAVED_FIXTURE", "idempotencyKey": "case-inspection-1"}).json()
    case_id = created["caseResults"][0]["caseExecutionId"]

    response = client.get(f"/api/v1/evaluation-runs/{created['evaluationRunId']}/cases/{case_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["transcriptText"]
    assert payload["candidate"]["noteBody"]
    assert isinstance(payload["expectedFindings"], list)
    assert isinstance(payload["actualFindings"], list)
    assert isinstance(payload["disagreements"], list)
    assert "modelId" in payload["configuration"]
    assert payload["benchmark"]["datasetVersion"] == dataset.dataset_version
    assert payload["expectedFindings"][0]["sourceEvidenceSpans"]

