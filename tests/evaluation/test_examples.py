from __future__ import annotations

from evaluation.adapters import DeterministicFixtureAdapter
from evaluation.benchmark import default_dataset
from evaluation.examples import SavedExampleRegistry
from evaluation.repository import SQLiteEvaluationRepository
from evaluation.runner import EvaluationRunner
from evaluation.contracts import EvaluationRunRequest


def test_saved_example_is_a_historical_reference_and_live_run_gets_new_identity(tmp_path) -> None:
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(tmp_path / "runs.sqlite3")
    runner = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=repo)
    run = runner.execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="VALIDATION", executionMode="MOCKED_PROVIDER", idempotencyKey="example-run"))
    registry = SavedExampleRegistry(repo)
    example = registry.register(run.evaluation_run_id, label="held example")
    saved = registry.get(example.saved_example_id)
    assert saved["origin"] == "HISTORICAL_SAVED_RESULT"
    assert saved["evaluationRunId"] == run.evaluation_run_id
    fresh = runner.execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit="VALIDATION", executionMode="MOCKED_PROVIDER", idempotencyKey="example-live"))
    assert fresh.evaluation_run_id != run.evaluation_run_id

