"""Thread-safe in-memory persistence for immutable note revisions."""

from __future__ import annotations

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
