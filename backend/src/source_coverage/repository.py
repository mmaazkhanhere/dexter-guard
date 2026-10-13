"""Repository ports and immutable in-memory records for coverage runs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Iterable, Protocol

from claim_extraction.models import Claim

from .contracts import CoverageRunSucceeded, CoverageRunFailed
from .extraction import SourceFactExtractionResult
from .matching import RelatedFinding


@dataclass(frozen=True)
class ClaimSetRecord:
    claim_set_id: str
    note_id: str
    note_revision: int
    resident_test_id: str
    source_id: str
    source_version: int
    claims: tuple[Claim, ...]


class SourceFactExtractionRepository(Protocol):
    def get(self, extraction_run_id: str) -> SourceFactExtractionResult: ...


class ClaimSetRepository(Protocol):
    def get(self, claim_set_id: str) -> ClaimSetRecord: ...


class RelatedFindingRepository(Protocol):
    def list(self, *, source_id: str, source_version: int, fact_ids: tuple[str, ...], claim_ids: tuple[str, ...]) -> tuple[RelatedFinding, ...]: ...


class CoverageRunRepository(Protocol):
    def get_by_idempotency(self, idempotency_key: str) -> CoverageRunSucceeded | CoverageRunFailed | None: ...

    def append(self, run: CoverageRunSucceeded | CoverageRunFailed) -> CoverageRunSucceeded | CoverageRunFailed: ...


class InMemorySourceFactExtractionRepository:
    def __init__(self, results: Iterable[SourceFactExtractionResult] = ()) -> None:
        self._items = {item.extraction_run_id: item for item in results}

    def get(self, extraction_run_id: str) -> SourceFactExtractionResult:
        try:
            return deepcopy(self._items[extraction_run_id])
        except KeyError as error:
            raise KeyError(extraction_run_id) from error


class InMemoryClaimSetRepository:
    def __init__(self, records: Iterable[ClaimSetRecord] = ()) -> None:
        self._items = {item.claim_set_id: item for item in records}

    def get(self, claim_set_id: str) -> ClaimSetRecord:
        try:
            return deepcopy(self._items[claim_set_id])
        except KeyError as error:
            raise KeyError(claim_set_id) from error


class InMemoryRelatedFindingRepository:
    def __init__(self, findings: Iterable[RelatedFinding] = ()) -> None:
        self._items = tuple(findings)

    def list(self, *, source_id: str, source_version: int, fact_ids: tuple[str, ...], claim_ids: tuple[str, ...]) -> tuple[RelatedFinding, ...]:
        return tuple(
            item for item in self._items
            if item.source_id == source_id and item.source_version == source_version
            and (item.source_fact_id in fact_ids or item.claim_id in claim_ids)
        )


class InMemoryCoverageRunRepository:
    def __init__(self) -> None:
        self.runs: list[CoverageRunSucceeded | CoverageRunFailed] = []
        self._by_key: dict[str, CoverageRunSucceeded | CoverageRunFailed] = {}
        self._lock = RLock()

    def get_by_idempotency(self, idempotency_key: str) -> CoverageRunSucceeded | CoverageRunFailed | None:
        with self._lock:
            run = self._by_key.get(idempotency_key)
            return run.model_copy(deep=True) if run is not None else None

    def append(self, run: CoverageRunSucceeded | CoverageRunFailed) -> CoverageRunSucceeded | CoverageRunFailed:
        with self._lock:
            if run.idempotency_key in self._by_key:
                raise RuntimeError("idempotency key already persisted")
            stored = run.model_copy(deep=True)
            self._by_key[run.idempotency_key] = stored
            self.runs.append(stored)
            return stored.model_copy(deep=True)
