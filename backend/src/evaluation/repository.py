from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock

from .contracts import BenchmarkDataset, EvaluationRun


class EvaluationRepositoryError(RuntimeError):
    pass


class IdempotencyConflict(EvaluationRepositoryError):
    pass


class SQLiteEvaluationRepository:
    """Append-only local store for versioned datasets and terminal evaluation runs."""

    def __init__(self, database_path: str | Path = "data/evaluation.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evaluation_datasets (
                    dataset_id TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(dataset_id, dataset_version)
                );
                CREATE TABLE IF NOT EXISTS evaluation_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    input_digest TEXT NOT NULL,
                    evaluation_run_id TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    evaluation_run_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def save_dataset(self, dataset: BenchmarkDataset) -> BenchmarkDataset:
        payload = _json(dataset)
        with self._lock, self._connection:
            row = self._connection.execute("SELECT payload_json FROM evaluation_datasets WHERE dataset_id=? AND dataset_version=?", (dataset.dataset_id, dataset.dataset_version)).fetchone()
            if row is not None and row["payload_json"] != payload:
                raise EvaluationRepositoryError("dataset version is immutable")
            if row is None:
                self._connection.execute("INSERT INTO evaluation_datasets(dataset_id,dataset_version,content_hash,payload_json) VALUES (?,?,?,?)", (dataset.dataset_id, dataset.dataset_version, dataset.content_hash, payload))
        return dataset

    def get_dataset(self, dataset_id: str, dataset_version: str) -> BenchmarkDataset | None:
        with self._lock:
            row = self._connection.execute("SELECT payload_json FROM evaluation_datasets WHERE dataset_id=? AND dataset_version=?", (dataset_id, dataset_version)).fetchone()
        return BenchmarkDataset.model_validate_json(row["payload_json"]) if row else None

    def reserve(self, idempotency_key: str, input_digest: str, run_id: str) -> bool:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute("SELECT input_digest FROM evaluation_idempotency WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                if row:
                    self._connection.commit()
                    if row["input_digest"] != input_digest:
                        raise IdempotencyConflict("idempotency key is bound to a different request")
                    return False
                self._connection.execute("INSERT INTO evaluation_idempotency(idempotency_key,input_digest,evaluation_run_id) VALUES (?,?,?)", (idempotency_key, input_digest, run_id))
                self._connection.commit()
                return True
            except Exception:
                self._connection.rollback()
                raise

    def save_run(self, run: EvaluationRun) -> EvaluationRun:
        payload = _json(run)
        with self._lock, self._connection:
            row = self._connection.execute("SELECT payload_json FROM evaluation_runs WHERE evaluation_run_id=?", (run.evaluation_run_id,)).fetchone()
            if row is not None:
                if row["payload_json"] != payload:
                    raise EvaluationRepositoryError("terminal evaluation run is immutable")
            else:
                self._connection.execute("INSERT INTO evaluation_runs(evaluation_run_id,payload_json,created_at) VALUES (?,?,?)", (run.evaluation_run_id, payload, run.started_at.isoformat()))
        return run

    def get_run(self, run_id: str) -> EvaluationRun | None:
        with self._lock:
            row = self._connection.execute("SELECT payload_json FROM evaluation_runs WHERE evaluation_run_id=?", (run_id,)).fetchone()
        return EvaluationRun.model_validate_json(row["payload_json"]) if row else None

    def run_id_for_idempotency(self, idempotency_key: str) -> str | None:
        with self._lock:
            row = self._connection.execute("SELECT evaluation_run_id FROM evaluation_idempotency WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        return row["evaluation_run_id"] if row else None

    def list_runs(self) -> tuple[EvaluationRun, ...]:
        with self._lock:
            rows = self._connection.execute("SELECT payload_json FROM evaluation_runs ORDER BY created_at, evaluation_run_id").fetchall()
        return tuple(EvaluationRun.model_validate_json(row["payload_json"]) for row in rows)

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", by_alias=True)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

