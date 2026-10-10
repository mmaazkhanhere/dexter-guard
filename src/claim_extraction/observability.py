"""Content-free extraction metrics and redacted event logging."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ExtractionMetricsSnapshot:
    provider_attempts: int
    provider_failures: int
    successful_results: int
    empty_results: int
    validation_failures: int


class ExtractionMetrics:
    def __init__(self) -> None:
        self._values = {
            "provider_attempts": 0,
            "provider_failures": 0,
            "successful_results": 0,
            "empty_results": 0,
            "validation_failures": 0,
        }
        self._lock = Lock()

    def increment(self, name: str) -> None:
        with self._lock:
            if name in self._values:
                self._values[name] += 1

    def snapshot(self) -> ExtractionMetricsSnapshot:
        with self._lock:
            return ExtractionMetricsSnapshot(**self._values)


class InMemoryExtractionLogger:
    """Test logger that accepts metadata only and never stores note content."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []
        self._lock = Lock()

    def event(self, name: str, **metadata: object) -> None:
        forbidden = {"note", "note_text", "claim", "claim_text", "prompt", "transcript"}
        safe = {key: value for key, value in metadata.items() if key not in forbidden}
        with self._lock:
            self.events.append((name, safe))
