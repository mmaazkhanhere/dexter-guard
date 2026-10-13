from __future__ import annotations

import argparse
import json

from .adapters import DeterministicFixtureAdapter
from .benchmark import default_dataset
from .contracts import EvaluationRunRequest
from .report import build_report
from .repository import SQLiteEvaluationRepository
from .runner import EvaluationRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic German Spec 008 evaluation headlessly")
    parser.add_argument("--split", choices=["DEVELOPMENT", "VALIDATION", "HELD_OUT"], required=True)
    parser.add_argument("--database", default="data/evaluation.sqlite3")
    parser.add_argument("--idempotency-key", default="cli-evaluation")
    args = parser.parse_args(argv)
    dataset = default_dataset()
    repo = SQLiteEvaluationRepository(args.database)
    run = EvaluationRunner(dataset=dataset, adapter=DeterministicFixtureAdapter(), repository=repo).execute(EvaluationRunRequest(subjectKind="BENCHMARK", datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version, datasetHash=dataset.content_hash, selectedSplit=args.split, executionMode="MOCKED_PROVIDER", idempotencyKey=args.idempotency_key))
    print(json.dumps(build_report(run), ensure_ascii=False, indent=2))
    return 0 if run.status.value in {"SUCCEEDED", "PARTIALLY_FAILED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

