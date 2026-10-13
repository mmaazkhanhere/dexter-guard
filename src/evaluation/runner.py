from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from .contracts import BenchmarkDataset, EvaluationRun, FailureSummary, RunConfiguration, RunStatus, InferenceParameters


def make_terminal_run(dataset: BenchmarkDataset, *, selected_split: str) -> EvaluationRun:
    cases = tuple(case for case in dataset.scenarios if case.split.value == selected_split)
    selection_digest = hashlib.sha256("|".join(case.scenario_id for case in cases).encode()).hexdigest()
    now = datetime.now(timezone.utc)
    configuration = RunConfiguration(
        codeVersion="working-tree", environmentId="local-synthetic", modelProvider=None, modelId=None, modelVersion=None,
        promptVersionsAndHashes=(), inferenceParameters=InferenceParameters(), ruleVersionsAndRulesetVersions=(),
        upstreamContractVersions=(), fixtureMode="SAVED_FIXTURE", pricingAssumptionsVersion=None,
        matchingPolicyVersion="EVALUATION_MATCHING-v1", randomSeed=0,
    )
    return EvaluationRun(
        evaluationRunId=f"eval-{uuid4().hex}", origin="NEWLY_EXECUTED", runPurpose="BENCHMARK_EVALUATION",
        scoringState="SCORED", status=RunStatus.SUCCEEDED, datasetId=dataset.dataset_id, datasetVersion=dataset.dataset_version,
        datasetHash=dataset.content_hash, selectedSplit=selected_split, selectionDigest=selection_digest,
        configuration=configuration, startedAt=now, completedAt=now, caseResults=(), aggregateMetrics=(), comparison=None,
        failureSummary=FailureSummary(failedCases=0, invalidOutputCases=0, unscorableCases=0, interruptedCases=0, failureCodes=()),
    )

