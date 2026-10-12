"""Minimized validation telemetry with no transcript or claim text fields."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

from .contracts import ValidationRun


class ValidationTelemetry(Protocol):
    def record(self, run: ValidationRun) -> None: ...


@dataclass(frozen=True)
class ValidationTelemetryEvent:
    validation_run_id: str
    engine_version: str
    ruleset_version: str
    outcome_counts: dict[str, int]
    rule_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass
class InMemoryValidationTelemetry:
    events: list[ValidationTelemetryEvent] = field(default_factory=list)

    def record(self, run: ValidationRun) -> None:
        outcomes = Counter(item.outcome.value for item in run.findings)
        self.events.append(
            ValidationTelemetryEvent(
                validation_run_id=run.validation_run_id,
                engine_version=run.engine_version,
                ruleset_version=run.ruleset_version,
                outcome_counts=dict(outcomes),
                rule_ids=tuple(item.rule_id for item in run.findings),
                reason_codes=tuple(item.reason_code.value for item in run.findings),
            )
        )

