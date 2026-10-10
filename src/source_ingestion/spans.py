"""Deterministic, exact-version source-span validation and resolution."""

from __future__ import annotations

from .contracts import ResolvedSourceSpan, SourceSpan
from .errors import ErrorCode, SourceError
from .repository import SourceRepository


def unicode_scalar_value_length(text: str) -> int:
    """Return the number of Python Unicode code points in the exact stored text."""

    return len(text)


def validate_span_boundaries(span: SourceSpan, transcript_text: str) -> None:
    length = unicode_scalar_value_length(transcript_text)
    if not 0 <= span.start < span.end <= length:
        raise SourceError(
            ErrorCode.INVALID_SOURCE_SPAN,
            "The source span must satisfy 0 <= start < end <= transcript length.",
            "start" if span.start >= span.end or span.start < 0 else "end",
        )


def resolve_source_span(span: SourceSpan, repository: SourceRepository) -> ResolvedSourceSpan:
    """Resolve only against the exact source/version named by ``span``."""

    document = repository.get(span.source_id, span.source_version)
    validate_span_boundaries(span, document.transcript_text)
    excerpt = document.transcript_text[span.start : span.end]
    return ResolvedSourceSpan(**span.model_dump(), text=excerpt)
