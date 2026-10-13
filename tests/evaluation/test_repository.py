from __future__ import annotations

from evaluation.benchmark import default_dataset
from evaluation.repository import IdempotencyConflict, SQLiteEvaluationRepository
from evaluation.runner import make_terminal_run


def test_sqlite_repository_restarts_and_keeps_terminal_runs_immutable(tmp_path) -> None:
    path = tmp_path / "evaluation.sqlite3"
    repo = SQLiteEvaluationRepository(path)
    dataset = default_dataset()
    repo.save_dataset(dataset)
    run = make_terminal_run(dataset, selected_split="HELD_OUT")
    assert repo.reserve("key", "digest", run.evaluation_run_id) is True
    repo.save_run(run)
    repo.close()
    restarted = SQLiteEvaluationRepository(path)
    assert restarted.get_run(run.evaluation_run_id) == run
    assert restarted.get_dataset(dataset.dataset_id, dataset.dataset_version) == dataset
    assert restarted.reserve("key", "digest", "another") is False
    try:
        restarted.reserve("key", "different", "third")
    except IdempotencyConflict:
        pass
    else:
        raise AssertionError("conflicting idempotency replay was accepted")
    restarted.close()


def test_repository_rejects_mutating_same_run_id(tmp_path) -> None:
    repo = SQLiteEvaluationRepository(tmp_path / "evaluation.sqlite3")
    dataset = default_dataset()
    run = make_terminal_run(dataset, selected_split="DEVELOPMENT")
    repo.save_run(run)
    changed = run.model_copy(update={"status": "FAILED"})
    try:
        repo.save_run(changed)
    except Exception as exc:
        assert "immutable" in str(exc).lower()
    else:
        raise AssertionError("mutable terminal run accepted")

