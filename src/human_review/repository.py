from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any
import sqlite3
from pathlib import Path

from .contracts import AuditEvent, FullNoteVerification, NoteDisposition, ReviewDecision, ReviewFinding, SuggestedCorrection


class ReviewRepositoryError(RuntimeError):
    pass


class InMemoryReviewRepository:
    """Append-only review store used by the synthetic local PoC."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.notes: dict[tuple[str, int], Any] = {}
        self.latest: dict[str, int] = {}
        self.findings: dict[str, ReviewFinding] = {}
        self.decisions: list[ReviewDecision] = []
        self.suggestions: dict[str, SuggestedCorrection] = {}
        self.verifications: dict[str, FullNoteVerification] = {}
        self.dispositions: list[NoteDisposition] = []
        self.events: dict[str, list[AuditEvent]] = {}
        self.idempotency: dict[tuple[str, str], str] = {}

    def append_event(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            events = self.events.setdefault(event.note_id, [])
            if any(existing.event_id == event.event_id for existing in events):
                raise ReviewRepositoryError("duplicate audit event")
            expected = len(events) + 1
            if event.sequence != expected:
                raise ReviewRepositoryError("audit sequence conflict")
            events.append(deepcopy(event))
            return deepcopy(event)

    def audit(self, note_id: str) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(deepcopy(self.events.get(note_id, [])))

    def bind_idempotency(self, operation: str, key: str, digest: str) -> None:
        with self._lock:
            existing = self.idempotency.get((operation, key))
            if existing is not None and existing != digest:
                raise ReviewRepositoryError("IDEMPOTENCY_KEY_CONFLICT")
            self.idempotency[(operation, key)] = digest


class SQLiteReviewRepository(InMemoryReviewRepository):
    """Local durable audit boundary; review records remain append-only."""

    def __init__(self, database_path: str | Path = "data/human_review.sqlite3") -> None:
        super().__init__()
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(note_id, sequence)
            )
        """)
        self._connection.commit()
        self._load_events()

    def _load_events(self) -> None:
        import json
        from .contracts import AuditEvent
        for row in self._connection.execute("SELECT payload_json FROM audit_events ORDER BY note_id, sequence"):
            event = AuditEvent.model_validate_json(row["payload_json"])
            self.events.setdefault(event.note_id, []).append(event)

    def append_event(self, event: AuditEvent) -> AuditEvent:
        import json
        saved = super().append_event(event)
        try:
            self._connection.execute(
                "INSERT INTO audit_events(event_id, note_id, sequence, payload_json) VALUES (?, ?, ?, ?)",
                (event.event_id, event.note_id, event.sequence, event.model_dump_json(by_alias=True)),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self.events[event.note_id].pop()
            raise ReviewRepositoryError("AUDIT_EVENT_CONFLICT") from error
        return saved
