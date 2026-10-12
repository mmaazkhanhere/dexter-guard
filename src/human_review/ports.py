from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UpstreamRun:
    run_id: str
    status: str
    source_id: str
    source_version: int
    note_id: str
    note_revision: int
    claim_set_id: str


class ClaimExtractionPort(Protocol):
    def extract(self, note_id: str, revision: int) -> UpstreamRun: ...


class EvidenceVerificationPort(Protocol):
    def evidence(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun: ...


class DeterministicValidationPort(Protocol):
    def validation(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun: ...


class SourceCoveragePort(Protocol):
    def coverage(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun: ...
