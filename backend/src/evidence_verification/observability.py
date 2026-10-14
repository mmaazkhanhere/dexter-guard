"""Content-free telemetry for verification runs."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Mapping


@dataclass(frozen=True)
class VerificationMetricsSnapshot:
    provider_attempts: int
    provider_failures: int
    successful_runs: int
    validation_failures: int
    evidence_integrity_failures: int
    persistence_failures: int
    span_integrity_failures: int = 0
    coverage_failures: int = 0
    warning_count: int = 0
    last_latency_ms: float | None = None
    model_versions: tuple[str, ...] = ()
    prompt_versions: tuple[str, ...] = ()
    policy_versions: tuple[str, ...] = ()
    rejection_reasons: tuple[tuple[str, int], ...] = ()
    token_usage: int = 0
    inference_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_known: bool = False


class VerificationMetrics:
    def __init__(self) -> None:
        self._values = {
            "provider_attempts": 0,
            "provider_failures": 0,
            "successful_runs": 0,
            "validation_failures": 0,
            "evidence_integrity_failures": 0,
            "persistence_failures": 0,
            "span_integrity_failures": 0,
            "coverage_failures": 0,
            "warning_count": 0,
        }
        self._last_latency_ms: float | None = None
        self._model_versions: set[str] = set()
        self._prompt_versions: set[str] = set()
        self._policy_versions: set[str] = set()
        self._rejection_reasons: dict[str, int] = {}
        self._token_usage = 0
        self._input_tokens = 0
        self._output_tokens = 0
        self._inference_cost = 0.0
        self._cost_known = False
        self._lock = Lock()

    def increment(self, name: str) -> None:
        with self._lock:
            if name in self._values:
                self._values[name] += 1

    def increment_by(self, name: str, amount: int) -> None:
        with self._lock:
            if name in self._values:
                self._values[name] += max(0, amount)

    def record_provider_usage(
        self,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        inference_cost: float | None = None,
    ) -> None:
        with self._lock:
            if input_tokens is not None:
                self._input_tokens += max(0, input_tokens)
                self._token_usage += max(0, input_tokens)
            if output_tokens is not None:
                self._output_tokens += max(0, output_tokens)
                self._token_usage += max(0, output_tokens)
            if inference_cost is not None:
                self._inference_cost += max(0.0, float(inference_cost))
                self._cost_known = True

    def record_terminal(
        self,
        *,
        status: str,
        latency_ms: float,
        metadata: Mapping[str, str | None],
        failure_code: str | None = None,
        token_usage: int | None = None,
        inference_cost: float | None = None,
        warning_count: int = 0,
    ) -> None:
        """Record only bounded, content-free run telemetry."""

        with self._lock:
            self._last_latency_ms = max(0.0, float(latency_ms))
            for key, target in (
                ("model_version", self._model_versions),
                ("prompt_version", self._prompt_versions),
            ):
                value = metadata.get(key)
                if value:
                    target.add(value)
            policy = metadata.get("annotation_policy_version") or metadata.get("policy_version")
            if policy:
                self._policy_versions.add(policy)
            if failure_code:
                self._rejection_reasons[failure_code] = self._rejection_reasons.get(failure_code, 0) + 1
            self._values["warning_count"] += max(0, warning_count)
            if token_usage is not None:
                self._token_usage += max(0, token_usage)
            if inference_cost is not None:
                self._inference_cost += max(0.0, float(inference_cost))
                self._cost_known = True

    def snapshot(self) -> VerificationMetricsSnapshot:
        with self._lock:
            return VerificationMetricsSnapshot(
                **self._values,
                last_latency_ms=self._last_latency_ms,
                model_versions=tuple(sorted(self._model_versions)),
                prompt_versions=tuple(sorted(self._prompt_versions)),
                policy_versions=tuple(sorted(self._policy_versions)),
                rejection_reasons=tuple(sorted(self._rejection_reasons.items())),
                token_usage=self._token_usage,
                inference_cost=self._inference_cost,
                input_tokens=self._input_tokens,
                output_tokens=self._output_tokens,
                cost_known=self._cost_known,
            )


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

