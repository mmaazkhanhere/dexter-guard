from __future__ import annotations

from collections.abc import Callable, Iterable

from .contracts import EvidenceDisplay, SourceSpan


class EvidenceContextService:
    """Validates source identity and derives excerpts; it never searches fallback text."""

    def __init__(self, source_reader: Callable[[str, int], object]) -> None:
        self.source_reader = source_reader

    def _source(self, source_id: str, version: int) -> str:
        value = self.source_reader(source_id, version)
        text = value[0] if isinstance(value, tuple) else getattr(value, "transcript_text")
        actual_id = value[1] if isinstance(value, tuple) and len(value) > 1 else source_id
        actual_version = value[2] if isinstance(value, tuple) and len(value) > 2 else version
        if (actual_id, actual_version) != (source_id, version):
            raise ValueError("source identity mismatch")
        return text

    def display(self, source_id: str, version: int, raw_spans: Iterable[tuple[str, int, int, int]]) -> EvidenceDisplay:
        spans = list(raw_spans)
        if not spans:
            return EvidenceDisplay(availability="MISSING", spans=(), excerpts=())
        try:
            text = self._source(source_id, version)
            validated: list[SourceSpan] = []
            excerpts: list[str] = []
            for raw_id, raw_version, start, end in spans:
                if (raw_id, raw_version) != (source_id, version) or start < 0 or end <= start or end > len(text):
                    raise ValueError("invalid source span")
                span = SourceSpan(sourceId=raw_id, sourceVersion=raw_version, start=start, end=end)
                excerpt = text[start:end]
                if not excerpt:
                    raise ValueError("empty source excerpt")
                validated.append(span)
                excerpts.append(excerpt)
            return EvidenceDisplay(availability="AVAILABLE", spans=tuple(validated), excerpts=tuple(excerpts))
        except Exception:
            return EvidenceDisplay(availability="INVALID", spans=(), excerpts=())
