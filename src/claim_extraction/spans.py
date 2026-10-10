"""Unicode-aware candidate-note span construction and validation."""

from __future__ import annotations

from pydantic import ValidationError

from .models import TextSpan


class SpanValidationError(ValueError):
    """Raised when a provider span does not identify the exact note text."""


def utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def utf16_offset(value: str, code_point_offset: int) -> int:
    if code_point_offset < 0 or code_point_offset > len(value):
        raise SpanValidationError("code-point offset is outside the note")
    return utf16_length(value[:code_point_offset])


def make_text_span(note_text: str, start: int, end: int) -> TextSpan:
    if start < 0 or end <= start or end > len(note_text):
        raise SpanValidationError("span must be a non-empty code-point range within the note")
    return TextSpan(
        startCodePoint=start,
        endCodePointExclusive=end,
        startUtf16=utf16_offset(note_text, start),
        endUtf16Exclusive=utf16_offset(note_text, end),
        text=note_text[start:end],
    )


def validate_text_span(span: TextSpan, note_text: str) -> TextSpan:
    """Require both coordinate systems to resolve to the declared substring."""

    start = span.start_code_point
    end = span.end_code_point_exclusive
    if start < 0 or end <= start or end > len(note_text):
        raise SpanValidationError("code-point span is outside the immutable note")
    expected_start_utf16 = utf16_offset(note_text, start)
    expected_end_utf16 = utf16_offset(note_text, end)
    if span.start_utf16 != expected_start_utf16 or span.end_utf16_exclusive != expected_end_utf16:
        raise SpanValidationError("UTF-16 coordinates do not match code-point coordinates")
    if note_text[start:end] != span.text:
        raise SpanValidationError("span text does not match the immutable note")
    return span


def parse_text_span(value: object) -> TextSpan:
    try:
        return value if isinstance(value, TextSpan) else TextSpan.model_validate(value)
    except (ValidationError, TypeError, ValueError) as error:
        raise SpanValidationError("provider returned a malformed text span") from error


class SpanValidator:
    """Small injectable facade used by callers that prefer an object port."""

    def validate(self, span: TextSpan, note_text: str) -> TextSpan:
        return validate_text_span(span, note_text)
