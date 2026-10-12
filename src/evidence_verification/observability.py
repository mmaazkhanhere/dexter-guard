"""Content-free telemetry for verification runs."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class VerificationMetricsSnapshot:
    provider_attempts: int
    provider_failures: int
    successful_runs: int
    validation_failures: int
    evidence_integrity_failures: int
    persistence_failures: int


class VerificationMetrics:
    def __init__(self) -> None:
        self._values = {
            "provider_attempts": 0,
            "provider_failures": 0,
            "successful_runs": 0,
            "validation_failures": 0,
            "evidence_integrity_failures": 0,
            "persistence_failures": 0,
        }
        self._lock = Lock()

    def increment(self, name: str) -> None:
        with self._lock:
            if name in self._values:
                self._values[name] += 1

    def snapshot(self) -> VerificationMetricsSnapshot:
        with self._lock:
            return VerificationMetricsSnapshot(**self._values)


class InMemoryVerificationLogger:
    """Structured test logger that drops transcript and model-content fields."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []
        self._lock = Lock()

    def event(self, name: str, **metadata: object) -> None:
        forbidden = {"transcript", "source_text", "claim", "claim_text", "prompt", "raw_output"}
        safe = {key: value for key, value in metadata.items() if key not in forbidden}
        with self._lock:
            self.events.append((name, safe))

