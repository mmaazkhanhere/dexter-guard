"""Application service for source creation, versioning, retrieval, and spans."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .contracts import (
    CreateSourceRequest,
    CreateSourceVersionRequest,
    ResolvedSourceSpan,
    SourceDocument,
    SourceSpan,
)
from .repository import InMemorySourceRepository, SourceRepository
from .spans import resolve_source_span
from .validation import (
    validate_create_source_request,
    validate_create_source_version_request,
    validate_source_span,
)


class SourceIngestionService:
    """Coordinates validation and repository operations without external services."""

    def __init__(
        self,
        repository: SourceRepository | None = None,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or InMemorySourceRepository()
        self._id_factory = id_factory or (lambda: f"source-{uuid4()}")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create_source(self, payload: Any) -> SourceDocument:
        request = payload if isinstance(payload, CreateSourceRequest) else validate_create_source_request(payload)
        document = SourceDocument(
            source_id=str(self._id_factory()),
            source_version=1,
            resident_test_id=request.resident_test_id,
            language=request.language,
            transcript_text=request.transcript_text,
            created_at=self._clock(),
        )
        return self.repository.create_initial(document)

    def create_source_version(self, source_id: str, payload: Any) -> SourceDocument:
        request = (
            payload
            if isinstance(payload, CreateSourceVersionRequest)
            else validate_create_source_version_request(payload)
        )
        return self.repository.create_next_version(
            source_id=source_id,
            expected_source_version=request.expected_source_version,
            transcript_text=request.transcript_text,
            created_at=self._clock(),
        )

    def get_source_version(self, source_id: str, source_version: int) -> SourceDocument:
        return self.repository.get(source_id, source_version)

    def resolve_span(self, payload: Any) -> ResolvedSourceSpan:
        span = payload if isinstance(payload, SourceSpan) else validate_source_span(payload)
        return resolve_source_span(span, self.repository)

    # Explicit aliases keep the transport-independent operations discoverable.
    submit_source = create_source
    create_version = create_source_version
    retrieve_source = get_source_version
    resolve_source_span = resolve_span
