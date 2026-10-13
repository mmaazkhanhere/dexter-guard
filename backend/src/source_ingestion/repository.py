"""Repository boundary for immutable source versions."""

from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Protocol

from .contracts import SourceDocument
from .errors import ErrorCode, SourceError


class SourceRepository(Protocol):
    """Persistence operations required by the source service."""

    def create_initial(self, document: SourceDocument) -> SourceDocument: ...

    def create_next_version(
        self,
        source_id: str,
        expected_source_version: int,
        transcript_text: str,
        created_at: datetime,
    ) -> SourceDocument: ...

    def get(self, source_id: str, source_version: int) -> SourceDocument: ...

    def source_exists(self, source_id: str) -> bool: ...

    def version_exists(self, source_id: str, source_version: int) -> bool: ...


class InMemorySourceRepository:
    """Thread-safe deterministic repository used by the proof of concept."""

    def __init__(self) -> None:
        self._documents: dict[tuple[str, int], SourceDocument] = {}
        self._latest_versions: dict[str, int] = {}
        self._lock = RLock()

    def create_initial(self, document: SourceDocument) -> SourceDocument:
        key = (document.source_id, document.source_version)
        with self._lock:
            if key in self._documents:
                raise SourceError(
                    ErrorCode.DUPLICATE_SOURCE_VERSION,
                    "The source version already exists.",
                    "source_id",
                )
            if document.source_version != 1 or document.source_id in self._latest_versions:
                raise SourceError(
                    ErrorCode.DUPLICATE_SOURCE_VERSION,
                    "An initial source must use a new source ID at version 1.",
                    "source_id",
                )
            self._documents[key] = document
            self._latest_versions[document.source_id] = document.source_version
            return document.model_copy(deep=True)

    def create_next_version(
        self,
        source_id: str,
        expected_source_version: int,
        transcript_text: str,
        created_at: datetime,
    ) -> SourceDocument:
        """Atomically compare-and-insert the next immutable version."""

        with self._lock:
            current_version = self._latest_versions.get(source_id)
            if current_version is None:
                raise SourceError(
                    ErrorCode.SOURCE_NOT_FOUND,
                    "The source ID does not exist.",
                    "source_id",
                )
            if current_version != expected_source_version:
                raise SourceError(
                    ErrorCode.VERSION_CONFLICT,
                    "The expected source version is stale or conflicts with another revision.",
                    "expected_source_version",
                )

            current = self._documents[(source_id, current_version)]
            next_version = current_version + 1
            key = (source_id, next_version)
            if key in self._documents:
                raise SourceError(
                    ErrorCode.VERSION_CONFLICT,
                    "The next source version is already claimed.",
                    "expected_source_version",
                )

            document = SourceDocument(
                source_id=source_id,
                source_version=next_version,
                resident_test_id=current.resident_test_id,
                language=current.language,
                transcript_text=transcript_text,
                created_at=created_at,
            )
            self._documents[key] = document
            self._latest_versions[source_id] = next_version
            return document.model_copy(deep=True)

    def get(self, source_id: str, source_version: int) -> SourceDocument:
        with self._lock:
            document = self._documents.get((source_id, source_version))
            if document is None:
                if source_id not in self._latest_versions:
                    raise SourceError(
                        ErrorCode.SOURCE_NOT_FOUND,
                        "The source ID does not exist.",
                        "source_id",
                    )
                raise SourceError(
                    ErrorCode.SOURCE_VERSION_NOT_FOUND,
                    "The requested source version does not exist.",
                    "source_version",
                )
            return document.model_copy(deep=True)

    def source_exists(self, source_id: str) -> bool:
        with self._lock:
            return source_id in self._latest_versions

    def version_exists(self, source_id: str, source_version: int) -> bool:
        with self._lock:
            return (source_id, source_version) in self._documents

    def count(self) -> int:
        with self._lock:
            return len(self._documents)
