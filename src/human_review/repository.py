from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

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
