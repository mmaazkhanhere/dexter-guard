from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable

from .contracts import (
    EvaluationCandidate,
    EvaluationCase,
    EvaluationFailure,
    ObservedFinding,
    SourceSpan,
    StageRunReference,
    UsageAndCost,
)


@dataclass(frozen=True)
class PipelineOutcome:
    findings: tuple[ObservedFinding, ...]
    stage_runs: tuple[StageRunReference, ...]
    latency_ms: float
    usage_and_cost: UsageAndCost
    failure: EvaluationFailure | None = None
    stage_latency_ms: dict[str, float | None] = field(default_factory=dict)
    # These aliases are pipeline metadata, not annotations.  The runner uses them
    # to translate implementation IDs into the immutable dataset's target IDs
    # after the engine has finished.  No expected error or expected status is
    # passed to the engine.
    claim_id_ordinals: tuple[tuple[str, int], ...] = ()
    source_fact_spans: tuple[tuple[str, tuple[SourceSpan, ...]], ...] = ()


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
            ), latency_ms=(perf_counter() - started) * 1000, usage_and_cost=UsageAndCost(inputTokens=None, outputTokens=None, retryCount=0, costState="UNAVAILABLE", estimatedCost=None, currency=None, pricingAssumptionsVersion="SYNTHETIC_FIXTURE-v1"),
        )


@dataclass(frozen=True)
class ReliabilityEngineInputs:
    """The complete input surface exposed to a real evaluation engine."""

    source_id: str
    source_version: int
    resident_test_id: str
    language: str
    transcript_text: str
    note_id: str
    note_revision: int
    note_body: str


class ReliabilityEngineEvaluationAdapter(PipelineAdapter):
    """Run the actual four-stage reliability pipeline for benchmark scoring.

    The adapter deliberately projects ``EvaluationCase`` and ``EvaluationCandidate``
    down to :class:`ReliabilityEngineInputs`.  In particular, ``error_instances``
    and expected claim statuses never cross this boundary.  The default engine is
    isolated per case, so benchmark execution cannot mutate application data.
    """

    def __init__(
        self,
        engine: Callable[[ReliabilityEngineInputs], PipelineOutcome] | None = None,
        *,
        evidence_verifier: object | None = None,
        claim_provider: object | None = None,
        coverage_matcher: object | None = None,
    ) -> None:
        self._evidence_verifier = evidence_verifier
        self._claim_provider = claim_provider
        self._coverage_matcher = coverage_matcher
        self._engine = engine or self._run_isolated_pipeline

    def evaluate(self, case: EvaluationCase, candidate: EvaluationCandidate) -> PipelineOutcome:
        # Keep this projection explicit.  It is the anti-label-leakage boundary.
        inputs = ReliabilityEngineInputs(
            source_id=case.source.source_id,
            source_version=case.source.source_version,
            resident_test_id=case.source.resident_test_id,
            language=case.source.language,
            transcript_text=case.source.transcript_text,
            note_id=candidate.note_id,
            note_revision=candidate.note_revision,
            note_body=candidate.note_body,
        )
        return self._engine(inputs)

    def _run_isolated_pipeline(self, inputs: ReliabilityEngineInputs) -> PipelineOutcome:
        """Materialize only the two textual inputs and execute production ports."""
        from human_review.repository import InMemoryReviewRepository
        from human_review.service import ReviewService
        from nursing_notes.repository import InMemoryNoteRepository
        from nursing_notes.service import NursingNoteService
        from source_ingestion.repository import InMemorySourceRepository
        from source_ingestion.service import SourceIngestionService
        from app.workflow import ReliabilityWorkflow

        started = perf_counter()
        stage_latency: dict[str, float | None] = {}
        if inputs.note_revision != 1:
            return PipelineOutcome(
                findings=(),
                stage_runs=(),
                latency_ms=(perf_counter() - started) * 1000,
                usage_and_cost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"),
                failure=EvaluationFailure(
                    code="UNSUPPORTED_NOTE_REVISION",
                    stage=None,
                    retryable=False,
                    message="The isolated benchmark adapter currently accepts revision 1 inputs only.",
                ),
                stage_latency_ms=stage_latency,
            )

        source_service = SourceIngestionService(
            repository=InMemorySourceRepository(),
            id_factory=lambda: inputs.source_id,
        )
        note_id_suffix = inputs.note_id.removeprefix("note-")
        note_service = NursingNoteService(
            source_service,
            repository=InMemoryNoteRepository(),
            id_factory=lambda: note_id_suffix,
        )
        review_service = ReviewService(InMemoryReviewRepository())
        source = source_service.create_source({
            "resident_test_id": inputs.resident_test_id,
            "language": inputs.language,
            "transcript_text": inputs.transcript_text,
        })
        note = note_service.import_note({
            "sourceId": source.source_id,
            "sourceVersion": source.source_version,
            "content": inputs.note_body,
            "externalOrigin": {"system": "EVALUATION_DATASET", "externalNoteId": inputs.note_id},
            "requestedBy": "evaluation-engine",
        })
        review_service.seed_note(note.note_id, source.source_id, source.source_version, note.content)
        workflow = ReliabilityWorkflow(
            source_service=source_service,
            note_service=note_service,
            review_service=review_service,
            claim_provider=self._claim_provider,
            evidence_verifier=self._evidence_verifier,
            coverage_matcher=self._coverage_matcher,
        )
        stage_latency["ADAPTER_SETUP"] = (perf_counter() - started) * 1000

        stage_runs: list[StageRunReference] = []
        stage_started = perf_counter()
        extraction = workflow.ports.extract(note.note_id, note.revision)
        stage_latency["CLAIM_EXTRACTION"] = (perf_counter() - stage_started) * 1000
        stage_runs.append(StageRunReference(stage="CLAIM_EXTRACTION", upstreamRunId=extraction.run_id, status=extraction.status))
        if extraction.status != "SUCCEEDED":
            return ReliabilityEngineEvaluationAdapter._failed_outcome(
                started, stage_runs, "CLAIM_EXTRACTION", "CLAIM_EXTRACTION_FAILED", stage_latency,
            )

        stage_started = perf_counter()
        evidence = workflow.ports.evidence(note.note_id, note.revision, extraction.claim_set_id)
        stage_latency["EVIDENCE_VERIFICATION"] = (perf_counter() - stage_started) * 1000
        stage_runs.append(StageRunReference(stage="EVIDENCE_VERIFICATION", upstreamRunId=evidence.run_id, status=evidence.status))
        stage_started = perf_counter()
        validation = workflow.ports.validation(note.note_id, note.revision, extraction.claim_set_id)
        stage_latency["DETERMINISTIC_VALIDATION"] = (perf_counter() - stage_started) * 1000
        stage_runs.append(StageRunReference(stage="DETERMINISTIC_VALIDATION", upstreamRunId=validation.run_id, status=validation.status))
        stage_started = perf_counter()
        coverage = workflow.ports.coverage(note.note_id, note.revision, extraction.claim_set_id)
        stage_latency["SOURCE_COVERAGE"] = (perf_counter() - stage_started) * 1000
        stage_runs.append(StageRunReference(stage="SOURCE_COVERAGE", upstreamRunId=coverage.run_id, status=coverage.status))

        findings: list[ObservedFinding] = []
        collection_started = perf_counter()
        claim_id_ordinals: list[tuple[str, int]] = []
        source_fact_spans: list[tuple[str, tuple[SourceSpan, ...]]] = []

        extraction_result = workflow.claim_service.repository.get_current_result(f"{note.note_id}:r{note.revision}")
        for ordinal, claim in enumerate(getattr(extraction_result, "claims", ()), start=1):
            claim_id_ordinals.append((claim.id, ordinal))

        extraction_facts = workflow.extraction_repository.get(f"source-facts-{extraction.claim_set_id}")
        for fact in extraction_facts.facts:
            source_fact_spans.append((
                fact.source_fact_id,
                tuple(SourceSpan(sourceId=span.source_id, sourceVersion=span.source_version, start=span.start, end=span.end) for span in fact.source_spans),
            ))

        evidence_run = workflow.evidence_service.repository.get(evidence.run_id)
        if evidence_run is not None and hasattr(evidence_run, "findings"):
            for index, finding in enumerate(evidence_run.findings):
                discrepancy = ",".join(item.value for item in finding.discrepancies) or None
                findings.append(ObservedFinding(
                    findingKey=f"{evidence.run_id}:{index}",
                    producer="SPEC_004",
                    upstreamRunId=evidence.run_id,
                    affectedClaimId=finding.claim_id,
                    affectedSourceFactId=None,
                    primaryStatusOrOutcome=finding.status.value,
                    discrepancyOrRule=discrepancy,
                    conflictingAttributeOrValue=None,
                    sourceSpans=tuple(SourceSpan(sourceId=span.source_id, sourceVersion=span.source_version, start=span.start, end=span.end) for span in finding.source_spans),
                    requiresCorrectionOrReview=finding.status.value != "SUPPORTED",
                ))

        validation_run = next((run for run in workflow.validation_runs.runs if run.validation_run_id == validation.run_id), None)
        if validation_run is not None:
            for index, finding in enumerate(validation_run.findings):
                findings.append(ObservedFinding(
                    findingKey=f"{validation.run_id}:{index}",
                    producer="SPEC_005",
                    upstreamRunId=validation.run_id,
                    affectedClaimId=finding.claim_id.removeprefix("dve-") if finding.claim_id else None,
                    affectedSourceFactId=finding.source_fact_id.removeprefix("dve-") if finding.source_fact_id else None,
                    primaryStatusOrOutcome=finding.outcome.value,
                    discrepancyOrRule=finding.reason_code.value,
                    conflictingAttributeOrValue="semantic_attribute" if finding.outcome.value != "NOT_EVALUABLE" else None,
                    sourceSpans=(),
                    requiresCorrectionOrReview=True,
                ))

        coverage_run = next((run for run in reversed(workflow.coverage_runs.runs) if run.coverage_run_id == coverage.run_id), None)
        if coverage_run is not None and hasattr(coverage_run, "findings"):
            for finding in coverage_run.findings:
                findings.append(ObservedFinding(
                    findingKey=finding.coverage_finding_id,
                    producer="SPEC_006",
                    upstreamRunId=coverage.run_id,
                    affectedClaimId=finding.matched_claim_ids[0] if finding.matched_claim_ids else None,
                    affectedSourceFactId=finding.source_fact_id,
                    primaryStatusOrOutcome=finding.status.value,
                    discrepancyOrRule="MISSING_EXPECTED_SOURCE_FACT" if finding.status.value == "MISSING" else finding.status.value,
                    conflictingAttributeOrValue=None,
                    sourceSpans=tuple(SourceSpan(sourceId=span.source_id, sourceVersion=span.source_version, start=span.start, end=span.end) for span in finding.source_spans),
                    requiresCorrectionOrReview=True,
                ))

        usage_and_cost = _pipeline_usage_and_cost(workflow, coverage_run)
        stage_latency["RESULT_COLLECTION"] = (perf_counter() - collection_started) * 1000

        return PipelineOutcome(
            findings=tuple(findings),
            stage_runs=tuple(stage_runs),
            latency_ms=(perf_counter() - started) * 1000,
            usage_and_cost=usage_and_cost,
            stage_latency_ms=stage_latency,
            claim_id_ordinals=tuple(claim_id_ordinals),
            source_fact_spans=tuple(source_fact_spans),
        )

    @staticmethod
    def _failed_outcome(started: float, stage_runs: list[StageRunReference], stage: str, code: str, stage_latency: dict[str, float | None]) -> PipelineOutcome:
        return PipelineOutcome(
            findings=(),
            stage_runs=tuple(stage_runs),
            latency_ms=(perf_counter() - started) * 1000,
            usage_and_cost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"),
            stage_latency_ms=stage_latency,
            failure=EvaluationFailure(code=code, stage=stage, retryable=False, message=f"{stage} did not complete successfully."),
        )


def _pipeline_usage_and_cost(workflow, coverage_run) -> UsageAndCost:
    """Aggregate content-free telemetry when a provider actually reports it."""
    evidence_snapshot = workflow.evidence_service.metrics.snapshot()
    execution = getattr(coverage_run, "execution_metrics", None)
    input_tokens = getattr(execution, "input_tokens", None)
    output_tokens = getattr(execution, "output_tokens", None)
    estimated_cost = getattr(execution, "inference_cost", None)
    if input_tokens is None and getattr(evidence_snapshot, "input_tokens", 0):
        input_tokens = evidence_snapshot.input_tokens
    if output_tokens is None and getattr(evidence_snapshot, "output_tokens", 0):
        output_tokens = evidence_snapshot.output_tokens
    if estimated_cost is None and getattr(evidence_snapshot, "cost_known", False):
        estimated_cost = evidence_snapshot.inference_cost
    cost_available = bool(getattr(evidence_snapshot, "cost_known", False)) or estimated_cost is not None
    return UsageAndCost(
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        retryCount=max(0, evidence_snapshot.provider_attempts - evidence_snapshot.successful_runs) + (getattr(execution, "retry_count", 0) or 0),
        costState="AVAILABLE" if cost_available else "UNAVAILABLE",
        estimatedCost=estimated_cost,
        currency="EUR" if cost_available else None,
        pricingAssumptionsVersion="PIPELINE_PROVIDER_REPORTED-v1" if cost_available else None,
    )


# Short alias for callers that prefer the user-facing name.
RealEvaluationAdapter = ReliabilityEngineEvaluationAdapter


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

