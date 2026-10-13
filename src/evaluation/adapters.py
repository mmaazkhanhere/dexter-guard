from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .contracts import EvaluationCandidate, EvaluationCase, EvaluationFailure, ObservedFinding, StageRunReference, UsageAndCost


@dataclass(frozen=True)
class PipelineOutcome:
    findings: tuple[ObservedFinding, ...]
    stage_runs: tuple[StageRunReference, ...]
    latency_ms: float
    usage_and_cost: UsageAndCost
    failure: EvaluationFailure | None = None


class PipelineAdapter:
    def evaluate(self, case: EvaluationCase, candidate: EvaluationCandidate) -> PipelineOutcome:
        raise NotImplementedError


class DeterministicFixtureAdapter(PipelineAdapter):
    """Saved synthetic fixture adapter; it stands in for upstream terminal outputs."""

    def evaluate(self, case: EvaluationCase, candidate: EvaluationCandidate) -> PipelineOutcome:
        started = perf_counter()
        findings: list[ObservedFinding] = []
        for error in candidate.error_instances:
            findings.append(ObservedFinding(
                findingKey=f"fixture-finding-{error.error_id}", producer="SPEC_004" if error.affected_annotated_claim_id else "SPEC_006",
                upstreamRunId=f"fixture-{case.scenario_id}", affectedClaimId=error.affected_annotated_claim_id,
                affectedSourceFactId=error.affected_source_fact_id, primaryStatusOrOutcome=error.expected_primary_status.value if error.expected_primary_status else "MISSING",
                discrepancyOrRule=error.required_discrepancy_or_rule, conflictingAttributeOrValue=error.conflicting_attribute,
                sourceSpans=error.source_evidence_spans, requiresCorrectionOrReview=True,
            ))
        return PipelineOutcome(
            findings=tuple(findings), stage_runs=(
                StageRunReference(stage="CLAIM_EXTRACTION", upstreamRunId=f"fixture-extraction-{case.scenario_id}", status="SUCCEEDED"),
                StageRunReference(stage="EVIDENCE_VERIFICATION", upstreamRunId=f"fixture-verification-{case.scenario_id}", status="SUCCEEDED"),
                StageRunReference(stage="DETERMINISTIC_VALIDATION", upstreamRunId=f"fixture-validation-{case.scenario_id}", status="SUCCEEDED"),
                StageRunReference(stage="SOURCE_COVERAGE", upstreamRunId=f"fixture-coverage-{case.scenario_id}", status="SUCCEEDED"),
            ), latency_ms=(perf_counter() - started) * 1000, usage_and_cost=UsageAndCost(inputTokens=0, outputTokens=0, retryCount=0, costState="AVAILABLE", estimatedCost=0.0, currency="EUR", pricingAssumptionsVersion="SYNTHETIC_FIXTURE-v1"),
        )


def observed_findings_from_upstream(*, producer: str, upstream_run_id: str, records: tuple[object, ...]) -> tuple[ObservedFinding, ...]:
    """Reference-only mapping of actual Spec 004/005/006 records; no re-verification."""
    output: list[ObservedFinding] = []
    for index, record in enumerate(records):
        get = (lambda name, default=None: record.get(name, default)) if isinstance(record, dict) else (lambda name, default=None: getattr(record, name, default))
        output.append(ObservedFinding(
            findingKey=str(get("finding_id", get("evidence_finding_id", get("coverage_finding_id", f"{upstream_run_id}-{index}")))),
            producer=producer, upstreamRunId=upstream_run_id, affectedClaimId=get("claim_id"), affectedSourceFactId=get("source_fact_id"),
            primaryStatusOrOutcome=str(get("status", get("outcome", "UNKNOWN"))), discrepancyOrRule=str(get("rule_code", get("code", ""))) or None,
            conflictingAttributeOrValue=None, sourceSpans=tuple(get("source_spans", ())), requiresCorrectionOrReview=True,
        ))
    return tuple(output)

