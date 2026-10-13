from __future__ import annotations

from datetime import datetime, timezone

import pytest

from evaluation.contracts import (
    CaseStatus, EvaluationRun, EvaluationRunRequest, InferenceParameters, MetricState,
    RateMetric, RunConfiguration, RunStatus,
)


def test_run_configuration_is_frozen_and_metric_has_raw_counts() -> None:
    config = RunConfiguration(
        codeVersion="test", environmentId="pytest", modelProvider=None, modelId=None, modelVersion=None,
        promptVersionsAndHashes=(), inferenceParameters=InferenceParameters(),
        ruleVersionsAndRulesetVersions=(), upstreamContractVersions=(), fixtureMode="MOCKED_PROVIDER",
        pricingAssumptionsVersion=None, matchingPolicyVersion="EVALUATION_MATCHING-v1", randomSeed=7,
    )
    with pytest.raises(Exception):
        config.code_version = "changed"  # type: ignore[misc]
    metric = RateMetric(
        metricId="critical-error-recall", metricKind="RATE", state=MetricState.SCORED,
        scorableCount=2, unscorableCount=0, failedCount=0, aggregationMethod="sum", policyVersion="EVALUATION_METRICS-v1",
        numerator=1, denominator=2, value=0.5,
        confidenceInterval={"method": "WILSON_95", "level": 0.95, "lower": 0.1, "upper": 0.9},
    )
    assert metric.denominator == 2


def test_synchronous_request_requires_explicit_split_and_no_arbitrary_demo_text() -> None:
    request = EvaluationRunRequest.model_validate({
        "subjectKind": "BENCHMARK", "datasetId": "d", "datasetVersion": "v", "datasetHash": "h",
        "selectedSplit": "HELD_OUT", "executionMode": "MOCKED_PROVIDER", "idempotencyKey": "k",
    })
    assert request.selected_split.value == "HELD_OUT"
    with pytest.raises(Exception):
        EvaluationRunRequest.model_validate({"subjectKind": "BENCHMARK", "datasetId": "d"})

