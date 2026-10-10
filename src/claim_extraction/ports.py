"""Dependency-inversion ports for note reading, providers, persistence, and metrics."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from .models import ExtractionResult


class NoteRevisionReader(Protocol):
    def read(self, note_revision_id: str) -> object: ...


class ClaimExtractionProvider(Protocol):
    provider_version: str | None
    model_version: str | None
    prompt_version: str | None

    def extract(self, note_text: str, **kwargs: object) -> object: ...


class ClaimRepository(Protocol):
    def save(self, result: ExtractionResult) -> ExtractionResult: ...

    def get_current_result(self, note_revision_id: str, extractor_version: str | None = None) -> ExtractionResult | None: ...


class ExtractionLogger(Protocol):
    def event(self, name: str, **metadata: object) -> None: ...


class ExtractionClock(Protocol):
    def __call__(self) -> datetime: ...


class ExtractionIdFactory(Protocol):
    def __call__(self) -> str: ...
