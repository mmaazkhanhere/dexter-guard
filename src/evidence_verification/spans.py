"""Exact Unicode code-point indexing for immutable evidence transcripts."""

from __future__ import annotations

from dataclasses import dataclass


class SourceSpanValidationError(ValueError):
    """Raised when a span cannot identify a non-empty source substring."""


@dataclass(frozen=True)
class SourceTextIndex:
    """Index the exact stored transcript without normalization or re-encoding.

    Offsets are zero-based, start-inclusive, and end-exclusive Unicode
    code-point offsets. Python's string indexing has exactly those semantics;
    in particular, it does not silently convert to UTF-16 code units.
    """

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("source text must be a string")

    @property
    def length(self) -> int:
        return len(self.text)

    def validate(self, start: int, end: int) -> None:
        if not isinstance(start, int) or isinstance(start, bool):
            raise SourceSpanValidationError("span start must be an integer")
        if not isinstance(end, int) or isinstance(end, bool):
            raise SourceSpanValidationError("span end must be an integer")
        if not 0 <= start < end <= self.length:
            raise SourceSpanValidationError(
                "span must satisfy 0 <= start < end <= source code-point length (end-exclusive)"
            )

    def derive(self, start: int, end: int) -> str:
        self.validate(start, end)
        return self.text[start:end]

    def matches(self, start: int, end: int, quotation: str) -> bool:
        return self.derive(start, end) == quotation


def derive_source_quote(source_text: str, start: int, end: int) -> str:
    """Return a source-derived quote after validating its code-point range."""

    return SourceTextIndex(source_text).derive(start, end)

