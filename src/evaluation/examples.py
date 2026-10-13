from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .repository import SQLiteEvaluationRepository


@dataclass(frozen=True)
class SavedExample:
    saved_example_id: str
    evaluation_run_id: str
    label: str
    saved_at: datetime


class SavedExampleRegistry:
    """Stores an immutable pointer; it never clones a run or performs fresh inference."""

    def __init__(self, repository: SQLiteEvaluationRepository) -> None:
        self.repository = repository
        self._examples: dict[str, SavedExample] = {}

    def register(self, evaluation_run_id: str, *, label: str) -> SavedExample:
        if self.repository.get_run(evaluation_run_id) is None:
            raise ValueError("evaluation run not found")
        example = SavedExample(f"example-{uuid4().hex}", evaluation_run_id, label, datetime.now(timezone.utc))
        self._examples[example.saved_example_id] = example
        return example

    def get(self, saved_example_id: str) -> dict[str, object]:
        example = self._examples.get(saved_example_id)
        if example is None:
            raise KeyError(saved_example_id)
        run = self.repository.get_run(example.evaluation_run_id)
        if run is None:
            raise KeyError(example.evaluation_run_id)
        return {"savedExampleId": example.saved_example_id, "evaluationRunId": run.evaluation_run_id, "label": example.label, "origin": "HISTORICAL_SAVED_RESULT", "savedAt": example.saved_at.isoformat(), "runStatus": run.status.value}

