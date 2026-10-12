"""Append-only verification-run persistence for the local synthetic PoC."""

from __future__ import annotations

import json
import sqlite3
from typing import Protocol
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import TypeAdapter

from .contracts import VerificationRun, VerificationRunRequest
from .validation import IdempotencyKeyConflictError, canonical_request_digest


class VerificationRepositoryError(RuntimeError):
    pass


class Reservation(Protocol):
    existing: VerificationRun | None
    created: bool


class VerificationRunRepository(Protocol):
    def reserve_or_replay(self, request: VerificationRunRequest, run_id: str) -> "Reservation": ...

    def save(self, run: VerificationRun) -> VerificationRun: ...

    def get(self, run_id: str) -> VerificationRun | None: ...


class IdempotencyReservation:
    def __init__(self, existing: VerificationRun | None, created: bool) -> None:
        self.existing = existing
        self.created = created


class InMemoryVerificationRepository:
    """Thread-safe append-only test and demo store."""

    def __init__(self) -> None:
        self._runs: dict[str, VerificationRun] = {}
        self._keys: dict[str, tuple[str, str]] = {}
        self._lock = RLock()

    def reserve_or_replay(self, request: VerificationRunRequest, run_id: str) -> IdempotencyReservation:
        digest = canonical_request_digest(request)
        with self._lock:
            prior = self._keys.get(request.idempotency_key)
            if prior is not None:
                prior_digest, prior_run_id = prior
                if prior_digest != digest:
                    raise IdempotencyKeyConflictError("idempotency key is already bound to a different request identity")
                return IdempotencyReservation(self._runs.get(prior_run_id), False)
            self._keys[request.idempotency_key] = (digest, run_id)
            return IdempotencyReservation(None, True)

    def save(self, run: VerificationRun) -> VerificationRun:
        with self._lock:
            prior = self._runs.get(run.verification_run_id)
            if prior is not None and prior != run:
                raise VerificationRepositoryError("verificationRunId is already bound to another result")
            self._runs[run.verification_run_id] = run
            return run

    def get(self, run_id: str) -> VerificationRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def count(self) -> int:
        with self._lock:
            return len(self._runs)


class SQLiteVerificationRepository:
    """SQLite-backed append-only run store with atomic key reservation."""

    def __init__(self, database_path: str | Path = "data/evidence_verification.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS verification_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    input_digest TEXT NOT NULL,
                    verification_run_id TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS verification_runs (
                    verification_run_id TEXT PRIMARY KEY,
                    input_digest TEXT NOT NULL,
                    run_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def reserve_or_replay(self, request: VerificationRunRequest, run_id: str) -> IdempotencyReservation:
        digest = canonical_request_digest(request)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    "SELECT input_digest, verification_run_id FROM verification_idempotency WHERE idempotency_key = ?",
                    (request.idempotency_key,),
                ).fetchone()
                if row is not None:
                    if row["input_digest"] != digest:
                        raise IdempotencyKeyConflictError("idempotency key is already bound to a different request identity")
                    existing_row = self._connection.execute(
                        "SELECT run_json FROM verification_runs WHERE verification_run_id = ?",
                        (row["verification_run_id"],),
                    ).fetchone()
                    self._connection.commit()
                    existing = _parse_run(existing_row["run_json"]) if existing_row is not None else None
                    return IdempotencyReservation(existing, False)
                self._connection.execute(
                    "INSERT INTO verification_idempotency (idempotency_key, input_digest, verification_run_id) VALUES (?, ?, ?)",
                    (request.idempotency_key, digest, run_id),
                )
                self._connection.commit()
                return IdempotencyReservation(None, True)
            except Exception:
                self._connection.rollback()
                raise

    def save(self, run: VerificationRun) -> VerificationRun:
        payload = json.dumps(run.model_dump(mode="json", by_alias=True), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                prior = self._connection.execute(
                    "SELECT run_json FROM verification_runs WHERE verification_run_id = ?",
                    (run.verification_run_id,),
                ).fetchone()
                if prior is not None:
                    if prior["run_json"] != payload:
                        raise VerificationRepositoryError("verificationRunId is already bound to another result")
                else:
                    self._connection.execute(
                        "INSERT INTO verification_runs (verification_run_id, input_digest, run_json, created_at) VALUES (?, ?, ?, ?)",
                        (run.verification_run_id, run.input_digest, payload, run.created_at.isoformat()),
                    )
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise
        return run

    def get(self, run_id: str) -> VerificationRun | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT run_json FROM verification_runs WHERE verification_run_id = ?", (run_id,)
            ).fetchone()
        return _parse_run(row["run_json"]) if row is not None else None

    def count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM verification_runs").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _parse_run(value: str) -> VerificationRun:
    return TypeAdapter(VerificationRun).validate_json(value)

