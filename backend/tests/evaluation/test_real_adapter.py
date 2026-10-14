from __future__ import annotations

from evaluation.adapters import (
    PipelineOutcome,
    RealEvaluationAdapter,
    ReliabilityEngineInputs,
)
from evaluation.benchmark import default_dataset
from evaluation.contracts import StageRunReference, UsageAndCost
from app.main import create_app


def test_real_adapter_exposes_only_transcript_and_candidate_note_to_engine() -> None:
    dataset = default_dataset()
    case = dataset.scenarios[3]
    candidate = case.candidate_notes[0]
    captured: list[ReliabilityEngineInputs] = []

    def spy(inputs: ReliabilityEngineInputs) -> PipelineOutcome:
        captured.append(inputs)
        return PipelineOutcome(
            findings=(),
            stage_runs=(StageRunReference(stage="CLAIM_EXTRACTION", upstreamRunId="spy", status="SUCCEEDED"),),
            latency_ms=1.0,
            usage_and_cost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"),
        )

    outcome = RealEvaluationAdapter(engine=spy).evaluate(case, candidate)

    assert outcome.findings == ()
    assert captured == [
        ReliabilityEngineInputs(
            source_id=case.source.source_id,
            source_version=case.source.source_version,
            resident_test_id=case.source.resident_test_id,
            language=case.source.language,
            transcript_text=case.source.transcript_text,
            note_id=candidate.note_id,
            note_revision=candidate.note_revision,
            note_body=candidate.note_body,
        )
    ]


def test_real_adapter_runs_the_actual_four_stage_pipeline_without_fixture_predictions() -> None:
    dataset = default_dataset()
    case = next(case for case in dataset.scenarios if "NUMERIC_MISMATCH" in case.tags)
    candidate = case.candidate_notes[0]

    outcome = RealEvaluationAdapter().evaluate(case, candidate)

    assert [run.stage for run in outcome.stage_runs] == [
        "CLAIM_EXTRACTION",
        "EVIDENCE_VERIFICATION",
        "DETERMINISTIC_VALIDATION",
        "SOURCE_COVERAGE",
    ]
    assert all(run.status == "SUCCEEDED" for run in outcome.stage_runs)
    assert outcome.usage_and_cost.cost_state == "UNAVAILABLE"
    assert {
        "ADAPTER_SETUP",
        "CLAIM_EXTRACTION",
        "EVIDENCE_VERIFICATION",
        "DETERMINISTIC_VALIDATION",
        "SOURCE_COVERAGE",
        "RESULT_COLLECTION",
    } <= outcome.stage_latency_ms.keys()
    assert all(value is not None and value >= 0 for value in outcome.stage_latency_ms.values())
    assert all(finding.upstream_run_id != f"fixture-{case.scenario_id}" for finding in outcome.findings)
    assert all(not finding.finding_key.startswith("fixture-finding-") for finding in outcome.findings)


def test_composed_application_uses_real_adapter_for_benchmark_runs() -> None:
    app = create_app()

    assert isinstance(app.state.evaluation_runner.adapter, RealEvaluationAdapter)
