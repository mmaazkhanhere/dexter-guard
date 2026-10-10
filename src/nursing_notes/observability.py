"""Content-free generation metrics for the synthetic local service."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class GenerationMetricsSnapshot:
    provider_attempts: int
    provider_failures: int
    successful_generations: int
    generation_rejections: int
    imports: int


class GenerationMetrics:
    """Thread-safe counters; no transcript, note, source, or resident content is retained."""

    def __init__(self) -> None:
        self._values = {
            "provider_attempts": 0,
            "provider_failures": 0,
            "successful_generations": 0,
            "generation_rejections": 0,
            "imports": 0,
        }
        self._lock = Lock()

    def increment(self, name: str) -> None:
        with self._lock:
            self._values[name] += 1

    def snapshot(self) -> GenerationMetricsSnapshot:
        with self._lock:
            return GenerationMetricsSnapshot(**self._values)
