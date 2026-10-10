"""Persistence boundaries for immutable nursing-note revisions."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Protocol

from .contracts import NoteRevisionRecord
from .errors import NoteError, NoteErrorCode


class NoteRepository(Protocol):
    def create(self, revision: NoteRevisionRecord) -> NoteRevisionRecord: ...

    def get(self, note_id: str, revision: int | None = None) -> NoteRevisionRecord: ...

    def count(self) -> int: ...

    def fact_count(self) -> int: ...


class InMemoryNoteRepository:
    """Deterministic repository used by the local synthetic-data PoC."""

    def __init__(self) -> None:
        self._revisions: dict[tuple[str, int], NoteRevisionRecord] = {}
        self._latest: dict[str, int] = {}
        self._lock = RLock()

    def create(self, revision: NoteRevisionRecord) -> NoteRevisionRecord:
        key = (revision.note_id, revision.revision)
        with self._lock:
            if key in self._revisions:
                raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note revision already exists.")
            latest = self._latest.get(revision.note_id)
            if revision.revision == 1:
                if latest is not None or revision.previous_revision_id is not None:
                    raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The initial note revision is invalid.")
            elif latest != revision.revision - 1 or revision.previous_revision_id != f"{revision.note_id}:r{latest}":
                raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note predecessor is stale or invalid.")
            self._revisions[key] = revision
            self._latest[revision.note_id] = revision.revision
            return revision.model_copy(deep=True)

    def get(self, note_id: str, revision: int | None = None) -> NoteRevisionRecord:
        with self._lock:
            selected = revision if revision is not None else self._latest.get(note_id)
            record = self._revisions.get((note_id, selected)) if selected is not None else None
            if record is None:
                raise NoteError(NoteErrorCode.NOTE_NOT_FOUND, "The requested note revision does not exist.")
            return record.model_copy(deep=True)

    def count(self) -> int:
        with self._lock:
            return len(self._revisions)

    def fact_count(self) -> int:
        with self._lock:
            return sum(len(record.facts) for record in self._revisions.values())


class SQLiteNoteRepository:
    """SQLite-backed append-only persistence for note revisions and facts."""

    def __init__(self, database_path: str | Path = "data/nursing_notes.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS note_revisions (
                    note_id TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    previous_revision_id TEXT,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status = 'DRAFT'),
                    origin TEXT NOT NULL CHECK (origin IN ('GENERATED', 'IMPORTED')),
                    source_id TEXT NOT NULL,
                    source_version INTEGER NOT NULL CHECK (source_version >= 1),
                    external_origin_json TEXT,
                    validation_run_id TEXT NOT NULL,
                    generation_run_id TEXT,
                    model_id TEXT,
                    prompt_version TEXT,
                    schema_version TEXT NOT NULL,
                    ruleset_version TEXT NOT NULL,
                    source_text_hash TEXT NOT NULL,
                    normalization_policy TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    PRIMARY KEY (note_id, revision),
                    CHECK ((origin = 'IMPORTED') = (external_origin_json IS NOT NULL))
                );

                CREATE TABLE IF NOT EXISTS nursing_facts (
                    note_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    fact_index INTEGER NOT NULL CHECK (fact_index >= 1),
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (note_id, revision, fact_index),
                    FOREIGN KEY (note_id, revision)
                        REFERENCES note_revisions(note_id, revision)
                        ON DELETE RESTRICT
                );
                """
            )

    def create(self, revision: NoteRevisionRecord) -> NoteRevisionRecord:
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                existing = self._connection.execute(
                    "SELECT 1 FROM note_revisions WHERE note_id = ? AND revision = ?",
                    (revision.note_id, revision.revision),
                ).fetchone()
                latest_row = self._connection.execute(
                    "SELECT revision FROM note_revisions WHERE note_id = ? ORDER BY revision DESC LIMIT 1",
                    (revision.note_id,),
                ).fetchone()
                latest = int(latest_row["revision"]) if latest_row else None
                if existing is not None:
                    raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note revision already exists.")
                if revision.revision == 1:
                    if latest is not None or revision.previous_revision_id is not None:
                        raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The initial note revision is invalid.")
                elif latest != revision.revision - 1 or revision.previous_revision_id != f"{revision.note_id}:r{latest}":
                    raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note predecessor is stale or invalid.")

                self._connection.execute(
                    """
                    INSERT INTO note_revisions (
                        note_id, revision, previous_revision_id, content, status, origin,
                        source_id, source_version, external_origin_json, validation_run_id,
                        generation_run_id, model_id, prompt_version, schema_version,
                        ruleset_version, source_text_hash, normalization_policy,
                        created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.note_id,
                        revision.revision,
                        revision.previous_revision_id,
                        revision.content,
                        revision.status,
                        revision.origin,
                        revision.source_id,
                        revision.source_version,
                        _json_dump(revision.external_origin.model_dump(mode="json", by_alias=True))
                        if revision.external_origin is not None
                        else None,
                        revision.validation_run_id,
                        revision.generation_run_id,
                        revision.model_id,
                        revision.prompt_version,
                        revision.schema_version,
                        revision.ruleset_version,
                        revision.source_text_hash,
                        revision.normalization_policy,
                        revision.created_at.isoformat(),
                        revision.created_by,
                    ),
                )
                self._connection.executemany(
                    "INSERT INTO nursing_facts (note_id, revision, fact_index, payload_json) VALUES (?, ?, ?, ?)",
                    [
                        (
                            revision.note_id,
                            revision.revision,
                            index,
                            _json_dump(fact.model_dump(mode="json", by_alias=True)),
                        )
                        for index, fact in enumerate(revision.facts, start=1)
                    ],
                )
                self._connection.commit()
            except NoteError:
                self._connection.rollback()
                raise
            except sqlite3.IntegrityError as error:
                self._connection.rollback()
                raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note revision conflicts with stored data.") from error
            except Exception:
                self._connection.rollback()
                raise
            return revision.model_copy(deep=True)

    def get(self, note_id: str, revision: int | None = None) -> NoteRevisionRecord:
        with self._lock:
            if revision is None:
                row = self._connection.execute(
                    "SELECT revision FROM note_revisions WHERE note_id = ? ORDER BY revision DESC LIMIT 1",
                    (note_id,),
                ).fetchone()
                revision = int(row["revision"]) if row else None
            row = (
                self._connection.execute(
                    "SELECT * FROM note_revisions WHERE note_id = ? AND revision = ?",
                    (note_id, revision),
                ).fetchone()
                if revision is not None
                else None
            )
            if row is None:
                raise NoteError(NoteErrorCode.NOTE_NOT_FOUND, "The requested note revision does not exist.")
            facts = self._connection.execute(
                "SELECT payload_json FROM nursing_facts WHERE note_id = ? AND revision = ? ORDER BY fact_index",
                (note_id, revision),
            ).fetchall()
            payload = {
                "noteId": row["note_id"],
                "revision": row["revision"],
                "previousRevisionId": row["previous_revision_id"],
                "content": row["content"],
                "status": row["status"],
                "origin": row["origin"],
                "sourceId": row["source_id"],
                "sourceVersion": row["source_version"],
                "externalOrigin": _json_load(row["external_origin_json"]),
                "validationRunId": row["validation_run_id"],
                "facts": [_json_load(item["payload_json"]) for item in facts],
                "generationRunId": row["generation_run_id"],
                "modelId": row["model_id"],
                "promptVersion": row["prompt_version"],
                "schemaVersion": row["schema_version"],
                "rulesetVersion": row["ruleset_version"],
                "sourceTextHash": row["source_text_hash"],
                "normalizationPolicy": row["normalization_policy"],
                "createdAt": row["created_at"],
                "createdBy": row["created_by"],
            }
            return NoteRevisionRecord.model_validate(payload)

    def count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM note_revisions").fetchone()[0])

    def fact_count(self) -> int:
        with self._lock:
            return int(self._connection.execute("SELECT COUNT(*) FROM nursing_facts").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _json_dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_load(value: str | None) -> object | None:
    return json.loads(value) if value is not None else None
