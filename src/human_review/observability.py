"""Content-minimized telemetry for the human-review boundary."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Mapping


@dataclass(frozen=True)
class ReviewMetricsSnapshot:
    verification_attempts: int
    verification_successes: int
    verification_failures: int
    verification_invalid: int
    approval_rejections: int
    stale_conflicts: int
    retry_replays: int
    last_latency_ms: float | None
    failure_codes: tuple[tuple[str, int], ...]


class ReviewMetrics:
    """Thread-safe counters containing identifiers/statuses, never source or note text."""

    def __init__(self) -> None:
        self._values = {
            "verification_attempts": 0,
            "verification_successes": 0,
            "verification_failures": 0,
            "verification_invalid": 0,
            "approval_rejections": 0,
            "stale_conflicts": 0,
            "retry_replays": 0,
        }
        self._last_latency_ms: float | None = None
        self._failure_codes: dict[str, int] = {}
        self._lock = Lock()

    def increment(self, name: str, *, failure_code: str | None = None) -> None:
        with self._lock:
            if name in self._values:
                self._values[name] += 1
            if failure_code:
                self._failure_codes[failure_code] = self._failure_codes.get(failure_code, 0) + 1

    def record_verification(self, *, status: str, latency_ms: float, failure_code: str | None = None) -> None:
        with self._lock:
            self._values["verification_attempts"] += 1
            bucket = {"VALID": "verification_successes", "INVALID": "verification_invalid"}.get(status, "verification_failures")
            self._values[bucket] += 1
            self._last_latency_ms = max(0.0, float(latency_ms))
            if failure_code:
                self._failure_codes[failure_code] = self._failure_codes.get(failure_code, 0) + 1

    def snapshot(self) -> ReviewMetricsSnapshot:
        with self._lock:
            return ReviewMetricsSnapshot(
                **self._values,
                last_latency_ms=self._last_latency_ms,
                failure_codes=tuple(sorted(self._failure_codes.items())),
            )


class InMemoryReviewLogger:
    """Structured logger that strips content-bearing fields before storage."""

    _FORBIDDEN = {"source_text", "transcript", "note", "note_text", "claim", "claim_text", "prompt", "raw_output", "replacement"}

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []
        self._lock = Lock()

    def event(self, name: str, **metadata: object) -> None:
        safe = {key: value for key, value in metadata.items() if key.lower() not in self._FORBIDDEN}
        with self._lock:
            self.events.append((name, safe))
