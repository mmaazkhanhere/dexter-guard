"""Injected repository ports and deterministic in-memory implementations."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Protocol

from .contracts import Alignment, Claim, SourceFact, TranscriptSnapshot, ValidationRun


class TranscriptRepository(Protocol):
    def get(self, source_id: str, source_version: int) -> TranscriptSnapshot: ...


class SourceFactRepository(Protocol):
    def get(self, source_fact_id: str) -> SourceFact: ...


class ClaimRepository(Protocol):
    def get(self, claim_id: str) -> Claim: ...


class AlignmentRepository(Protocol):
    def get(self, alignment_id: str) -> Alignment: ...


class ValidationRunRepository(Protocol):
    def append(self, run: ValidationRun) -> ValidationRun: ...


class InMemoryTranscriptRepository:
    def __init__(self, snapshots: Iterable[TranscriptSnapshot] = ()) -> None:
        self._items = {(item.source_id, item.source_version): item for item in snapshots}

    def get(self, source_id: str, source_version: int) -> TranscriptSnapshot:
        try:
            return self._items[(source_id, source_version)].model_copy(deep=True)
        except KeyError as error:
            raise LookupError((source_id, source_version)) from error


class InMemorySourceFactRepository:
    def __init__(self, facts: Iterable[SourceFact] = ()) -> None:
        self._items = {item.source_fact_id: item for item in facts}

    def get(self, source_fact_id: str) -> SourceFact:
        try:
            return self._items[source_fact_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError(source_fact_id) from error


class InMemoryClaimRepository:
    def __init__(self, claims: Iterable[Claim] = ()) -> None:
        self._items = {item.claim_id: item for item in claims}

    def get(self, claim_id: str) -> Claim:
        try:
            return self._items[claim_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError(claim_id) from error


class InMemoryAlignmentRepository:
    def __init__(self, alignments: Iterable[Alignment] = ()) -> None:
        self._items = {item.alignment_id: item for item in alignments}

    def get(self, alignment_id: str) -> Alignment:
        try:
            return self._items[alignment_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError(alignment_id) from error


class InMemoryValidationRunRepository:
    def __init__(self) -> None:
        self.runs: list[ValidationRun] = []

    def append(self, run: ValidationRun) -> ValidationRun:
        self.runs.append(run.model_copy(deep=True))
        return run.model_copy(deep=True)

