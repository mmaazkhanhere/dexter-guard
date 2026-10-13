from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, TypeVar


@dataclass(frozen=True)
class UpstreamRun:
    run_id: str
    status: str
    source_id: str
    source_version: int
    note_id: str
    note_revision: int
    claim_set_id: str
    unresolved_source_items: int = 0


class ClaimExtractionPort(Protocol):
    def extract(self, note_id: str, revision: int) -> UpstreamRun: ...


class EvidenceVerificationPort(Protocol):
    def evidence(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun: ...


class DeterministicValidationPort(Protocol):
    def validation(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun: ...


class SourceCoveragePort(Protocol):
    def coverage(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun: ...


T = TypeVar("T")


class ReferenceOnlyVerificationPorts:
    """Adapt upstream terminal-run readers without accepting source or claim text.

    Each callable must return an object exposing only terminal run metadata. The adapter copies
    those immutable references into ``UpstreamRun``; it never parses, recomputes, or promotes
    prose, transcript text, or candidate-note content.
    """

    def __init__(self, *, extract_claims, verify_evidence, validate_deterministically, read_coverage) -> None:
        self._extract_claims = extract_claims
        self._verify_evidence = verify_evidence
        self._validate_deterministically = validate_deterministically
        self._read_coverage = read_coverage

    @staticmethod
    def _metadata(run) -> UpstreamRun:
        required = ("run_id", "status", "source_id", "source_version", "note_id", "note_revision", "claim_set_id")
        if any(not hasattr(run, name) for name in required):
            raise ValueError("MALFORMED_UPSTREAM_RESULT")
        return UpstreamRun(
            run_id=run.run_id,
            status=run.status,
            source_id=run.source_id,
            source_version=run.source_version,
            note_id=run.note_id,
            note_revision=run.note_revision,
            claim_set_id=run.claim_set_id,
            unresolved_source_items=getattr(run, "unresolved_source_items", 0),
        )

    def extract(self, note_id: str, revision: int) -> UpstreamRun:
        return self._metadata(self._extract_claims(note_id, revision))

    def evidence(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        return self._metadata(self._verify_evidence(note_id, revision, claim_set_id))

    def validation(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        return self._metadata(self._validate_deterministically(note_id, revision, claim_set_id))

    def coverage(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        return self._metadata(self._read_coverage(note_id, revision, claim_set_id))


class RetryingVerificationPorts:
    """Bounded, deterministic retry wrapper for synchronous upstream adapters.

    Only transport-style timeouts are retried. A malformed result or any other failure is
    returned to the orchestrator as a terminal failure rather than being disguised as success.
    """

    def __init__(self, delegate, *, max_attempts: int = 2, on_retry: Callable[[str], None] | None = None) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.delegate = delegate
        self.max_attempts = max_attempts
        self.on_retry = on_retry

    def _call(self, operation: str, callback: Callable[[], T]) -> T:
        last_error: TimeoutError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return callback()
            except TimeoutError as error:
                last_error = error
                if attempt < self.max_attempts and self.on_retry:
                    self.on_retry(operation)
        assert last_error is not None
        raise last_error

    def extract(self, note_id: str, revision: int) -> UpstreamRun:
        return self._call("CLAIM_EXTRACTION", lambda: self.delegate.extract(note_id, revision))

    def evidence(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        return self._call("EVIDENCE_VERIFICATION", lambda: self.delegate.evidence(note_id, revision, claim_set_id))

    def validation(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        return self._call("DETERMINISTIC_VALIDATION", lambda: self.delegate.validation(note_id, revision, claim_set_id))

    def coverage(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        return self._call("SOURCE_COVERAGE", lambda: self.delegate.coverage(note_id, revision, claim_set_id))
