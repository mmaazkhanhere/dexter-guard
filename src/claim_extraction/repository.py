"""Append-only claim extraction result repositories."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from .models import ExtractionResult


class ClaimRepository(Protocol):
    def save(self, result: ExtractionResult) -> ExtractionResult: ...

    def get_current_result(self, note_revision_id: str, extractor_version: str | None = None) -> ExtractionResult | None: ...


class ClaimRepositoryError(RuntimeError):
    pass


class InMemoryClaimRepository:
    """Deterministic append-only repository for unit and integration tests."""

    def __init__(self) -> None:
        self._results: dict[str, ExtractionResult] = {}
        self._order: list[str] = []
        self._lock = RLock()

    def save(self, result: ExtractionResult) -> ExtractionResult:
        with self._lock:
            existing = self._results.get(result.extraction_run_id)
            if existing is not None:
                if existing != result:
                    raise ClaimRepositoryError("extractionRunId is already bound to another result")
                return existing
            self._results[result.extraction_run_id] = result
            self._order.append(result.extraction_run_id)
            return result.model_copy(deep=True)

    def get_current_result(self, note_revision_id: str, extractor_version: str | None = None) -> ExtractionResult | None:
        with self._lock:
            for run_id in reversed(self._order):
                result = self._results[run_id]
                if result.status.value not in {"SUCCEEDED", "EMPTY"}:
                    continue
                if result.note_revision_id != note_revision_id:
                    continue
                if extractor_version is not None and result.extractor_version != extractor_version:
                    continue
                return result.model_copy(deep=True)
        return None


class SQLiteClaimRepository:
    """SQLite persistence with append-only run history and revision-bound results."""

    def __init__(self, database_path: str | Path = "data/claim_extraction.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS claim_extraction_runs (
                    extraction_run_id TEXT PRIMARY KEY,
                    note_revision_id TEXT,
                    status TEXT NOT NULL,
                    extractor_version TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS extracted_claims (
                    extraction_run_id TEXT NOT NULL,
                    claim_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (extraction_run_id, claim_id),
                    FOREIGN KEY (extraction_run_id) REFERENCES claim_extraction_runs(extraction_run_id)
                );
                """
            )

    def save(self, result: ExtractionResult) -> ExtractionResult:
        payload = result.model_dump(mode="json", by_alias=True)
        note_revision_id = payload.get("noteRevisionId")
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                existing = self._connection.execute(
                    "SELECT result_json FROM claim_extraction_runs WHERE extraction_run_id = ?",
                    (result.extraction_run_id,),
                ).fetchone()
                encoded = _json_dump(payload)
                if existing is not None:
                    if existing["result_json"] != encoded:
                        raise ClaimRepositoryError("extractionRunId is already bound to another result")
                    self._connection.commit()
                    return result.model_copy(deep=True)
                self._connection.execute(
                    "INSERT INTO claim_extraction_runs (extraction_run_id, note_revision_id, status, extractor_version, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        result.extraction_run_id,
                        note_revision_id,
                        result.status.value,
                        result.extractor_version,
                        encoded,
                        result.extracted_at.isoformat(),
                    ),
                )
                self._connection.executemany(
                    "INSERT INTO extracted_claims (extraction_run_id, claim_id, ordinal, payload_json) VALUES (?, ?, ?, ?)",
                    [
                        (result.extraction_run_id, claim.id, claim.ordinal, _json_dump(claim.model_dump(mode="json", by_alias=True)))
                        for claim in result.claims
                    ],
                )
                self._connection.commit()
            except ClaimRepositoryError:
                self._connection.rollback()
                raise
            except Exception:
                self._connection.rollback()
                raise
        return result.model_copy(deep=True)

    def get_current_result(self, note_revision_id: str, extractor_version: str | None = None) -> ExtractionResult | None:
        query = "SELECT result_json FROM claim_extraction_runs WHERE note_revision_id = ? AND status IN ('SUCCEEDED', 'EMPTY')"
        parameters: list[object] = [note_revision_id]
        if extractor_version is not None:
            query += " AND extractor_version = ?"
            parameters.append(extractor_version)
        query += " ORDER BY rowid DESC LIMIT 1"
        with self._lock:
            row = self._connection.execute(query, parameters).fetchone()
        if row is None:
            return None
        return _validate_result_json(row["result_json"])

    def run_count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM claim_extraction_runs").fetchone()[0])

    def claim_count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM extracted_claims").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _validate_result_json(value: str) -> ExtractionResult:
    from pydantic import TypeAdapter

    from .models import ExtractionResult

    return TypeAdapter(ExtractionResult).validate_json(value)
