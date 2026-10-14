from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from .adapters import PipelineAdapter, PipelineOutcome
from .benchmark import default_dataset
from .comparison import compare_paired_cases
from .contracts import (
    BenchmarkDataset, CaseStatus, DatasetSplit, EvaluationCaseResult, EvaluationRun, EvaluationRunRequest, FailureSummary,
    FindingMatch, InferenceParameters, LatencyBreakdown, ObservedFinding, RunConfiguration, RunStatus, SourceFactScore, UsageAndCost,
)
from .dataset import DatasetValidationError, validate_dataset
from .matching import match_findings
from .metrics import calculate_metrics
from .observability import EvaluationTelemetry
from .repository import SQLiteEvaluationRepository


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


class EvaluationRunner:
    def __init__(self, *, dataset: BenchmarkDataset | None = None, adapter: PipelineAdapter, repository: SQLiteEvaluationRepository | None = None, telemetry: EvaluationTelemetry | None = None, code_version: str = "working-tree") -> None:
        self.dataset = dataset or default_dataset()
        self.adapter = adapter
        self.repository = repository
        self.telemetry = telemetry or EvaluationTelemetry()
        self.code_version = code_version

    def execute(self, request: EvaluationRunRequest) -> EvaluationRun:
        run_id = f"eval-{uuid4().hex}"
        request_digest = hashlib.sha256(request.model_dump_json(by_alias=True, exclude_none=True).encode()).hexdigest()
        if self.repository and not self.repository.reserve(request.idempotency_key, request_digest, run_id):
            prior_id = self.repository.run_id_for_idempotency(request.idempotency_key)
            prior = self.repository.get_run(prior_id) if prior_id else None
            if prior is not None:
                return prior
        if request.subject_kind == "SYNTHETIC_DEMO":
            run = self._demo_run(request, run_id)
            if self.repository:
                self.repository.save_run(run)
            return run
        try:
            if request.dataset_id != self.dataset.dataset_id or request.dataset_version != self.dataset.dataset_version or request.dataset_hash != self.dataset.content_hash:
                raise DatasetValidationError("requested dataset identity does not match immutable fixture")
            validate_dataset(self.dataset, request.selected_split)
        except DatasetValidationError as error:
            run = self._invalid_run(request, run_id, str(error))
            if self.repository:
                self.repository.save_run(run)
            return run
        selected = [case for case in self.dataset.scenarios if case.split == request.selected_split]
        started = datetime.now(timezone.utc)
        results: list[EvaluationCaseResult] = []
        for case in selected:
            for candidate in case.candidate_notes:
                results.append(self._execute_case(case, candidate))
        critical_total = sum(sum(error.severity.value == "CRITICAL" for error in candidate.error_instances) for case in selected for candidate in case.candidate_notes)
        critical_detected = sum(sum(match.disposition.value == "MATCHED" and any(error.error_id == match.error_id and error.severity.value == "CRITICAL" for error in candidate.error_instances) for match in result.match_results) for case, result in zip((case for case in selected for _ in case.candidate_notes), results) for candidate in case.candidate_notes)
        scenario_total = sum(any(error.severity.value == "CRITICAL" for candidate in case.candidate_notes for error in candidate.error_instances) for case in selected)
        scenario_detected = sum(any(error.severity.value == "CRITICAL" for candidate in case.candidate_notes for error in candidate.error_instances) and all(any(match.error_id == error.error_id and match.disposition.value == "MATCHED" for match in result.match_results) for candidate in case.candidate_notes for error in candidate.error_instances if error.severity.value == "CRITICAL") for case, result in zip(selected, results))
        supported_claims = sum(sum(claim.expected_primary_status.value == "SUPPORTED" and claim.scorable for claim in candidate.annotated_claims) for case in selected for candidate in case.candidate_notes)
        false_positives = sum(sum(finding.requires_correction_or_review and any(claim.claim_id == finding.affected_claim_id and claim.expected_primary_status.value == "SUPPORTED" for claim in candidate.annotated_claims) for finding in result.observed_findings) for case, result in zip(selected, results) for candidate in case.candidate_notes)
        annotated_claims = sum(sum(claim.scorable for claim in candidate.annotated_claims) for case in selected for candidate in case.candidate_notes)
        expected_facts = sum(sum(fact.expectation != "CONTEXTUAL" and (fact.applicable_to_candidate_ids == "ALL" or candidate.candidate_id in fact.applicable_to_candidate_ids) for fact in case.reference_facts) for case in selected for candidate in case.candidate_notes)
        covered_facts = sum(sum(score.faithfully_covered for score in result.completeness_results) for result in results)
        metrics = calculate_metrics(results, supported_claims=supported_claims, supported_false_positives=false_positives, annotated_claims=annotated_claims, expected_facts=expected_facts, covered_facts=covered_facts, critical_errors=critical_total, detected_critical_errors=critical_detected, scenario_critical_total=scenario_total, scenario_critical_detected=scenario_detected)
        failed = sum(result.status in {CaseStatus.FAILED, CaseStatus.INVALID_OUTPUT} for result in results)
        unscorable = sum(result.status is CaseStatus.UNSCORABLE for result in results)
        status = RunStatus.PARTIALLY_FAILED if failed or unscorable else RunStatus.SUCCEEDED
        completed = datetime.now(timezone.utc)
        run = EvaluationRun(
            evaluationRunId=run_id, origin="NEWLY_EXECUTED", runPurpose="BENCHMARK_EVALUATION", scoringState="SCORED", status=status,
            datasetId=self.dataset.dataset_id, datasetVersion=self.dataset.dataset_version, datasetHash=self.dataset.content_hash, selectedSplit=request.selected_split,
            selectionDigest=hashlib.sha256("|".join(case.scenario_id for case in selected).encode()).hexdigest(), configuration=self._configuration(request),
            startedAt=started, completedAt=completed, caseResults=tuple(results), aggregateMetrics=metrics, comparison=None,
            failureSummary=FailureSummary(failedCases=failed, invalidOutputCases=sum(result.status is CaseStatus.INVALID_OUTPUT for result in results), unscorableCases=unscorable, interruptedCases=0, failureCodes=tuple(sorted({result.failure.code for result in results if result.failure}))),
        )
        if self.repository:
            self.repository.save_run(run)
        return run

    def _execute_case(self, case, candidate) -> EvaluationCaseResult:
        started = perf_counter()
        try:
            outcome = self.adapter.evaluate(case, candidate)
            failure = outcome.failure
            status = CaseStatus.FAILED if failure else CaseStatus.SUCCEEDED
            findings = _canonicalize_findings(outcome, case, candidate)
            matches = match_findings(findings, candidate.error_instances) if not failure else tuple(FindingMatch(errorId=error.error_id, findingKey=None, disposition="FALSE_NEGATIVE", reasonCode="CASE_FAILED", specificityScore=None) for error in candidate.error_instances)
            scores = _completeness_scores(outcome, findings, case, candidate)
            return EvaluationCaseResult(caseExecutionId=f"case-{uuid4().hex}", scenarioId=case.scenario_id, candidateId=candidate.candidate_id, sourceId=case.source.source_id, sourceVersion=case.source.source_version, sourceTextHash=case.source.source_text_hash, noteId=candidate.note_id, noteRevision=candidate.note_revision, noteBodyHash=candidate.note_body_hash, status=status, stageRuns=outcome.stage_runs, observedFindings=findings, matchResults=matches, completenessResults=scores, reviewOutcome=None, latency=LatencyBreakdown(endToEndMilliseconds=outcome.latency_ms or (perf_counter() - started) * 1000), usageAndCost=outcome.usage_and_cost, failure=failure)
        except Exception as error:
            from .contracts import EvaluationFailure
            return EvaluationCaseResult(caseExecutionId=f"case-{uuid4().hex}", scenarioId=case.scenario_id, candidateId=candidate.candidate_id, sourceId=case.source.source_id, sourceVersion=case.source.source_version, sourceTextHash=case.source.source_text_hash, noteId=candidate.note_id, noteRevision=candidate.note_revision, noteBodyHash=candidate.note_body_hash, status=CaseStatus.FAILED, stageRuns=(), observedFindings=(), matchResults=(), completenessResults=(), reviewOutcome=None, latency=LatencyBreakdown(endToEndMilliseconds=(perf_counter() - started) * 1000), usageAndCost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"), failure=EvaluationFailure(code="EVALUATION_ADAPTER_FAILURE", stage=None, retryable=False, message=str(error)))

    def _configuration(self, request) -> RunConfiguration:
        is_live = request.execution_mode == "LIVE"
        return RunConfiguration(codeVersion=self.code_version, environmentId="local-synthetic", modelProvider=None, modelId=None, modelVersion=None, promptVersionsAndHashes=(), inferenceParameters=InferenceParameters(), ruleVersionsAndRulesetVersions=(), upstreamContractVersions=(
            {"name": "SPEC_004", "version": "EVIDENCE_STATUS-v1"}, {"name": "SPEC_006", "version": "SOURCE_COVERAGE-v1"},
        ), fixtureMode=request.execution_mode, pricingAssumptionsVersion=None if is_live else "SYNTHETIC_FIXTURE-v1", matchingPolicyVersion="EVALUATION_MATCHING-v1", randomSeed=0)

    def _invalid_run(self, request, run_id: str, reason: str) -> EvaluationRun:
        now = datetime.now(timezone.utc)
        return EvaluationRun(evaluationRunId=run_id, origin="NEWLY_EXECUTED", runPurpose="BENCHMARK_EVALUATION", scoringState="UNSCORABLE", status=RunStatus.INVALID_DATASET, datasetId=request.dataset_id, datasetVersion=request.dataset_version, datasetHash=request.dataset_hash, selectedSplit=request.selected_split, selectionDigest="invalid", configuration=self._configuration(request), startedAt=now, completedAt=now, caseResults=(), aggregateMetrics=(), comparison=None, failureSummary=FailureSummary(failedCases=0, invalidOutputCases=0, unscorableCases=0, interruptedCases=0, failureCodes=(f"INVALID_DATASET:{reason}",)))

    def _demo_run(self, request, run_id: str) -> EvaluationRun:
        now = datetime.now(timezone.utc)
        from .contracts import DemoInputReference
        return EvaluationRun(evaluationRunId=run_id, origin="NEWLY_EXECUTED", runPurpose="SYNTHETIC_DEMO_TRACKING", scoringState="DEMONSTRATION_ONLY", status=RunStatus.SUCCEEDED, datasetId=None, datasetVersion=None, datasetHash=None, selectedSplit=None, selectionDigest=hashlib.sha256(request.idempotency_key.encode()).hexdigest(), configuration=self._configuration(request), demoReference=DemoInputReference(sourceId=request.source_id, sourceVersion=request.source_version, noteId=request.note_id, noteRevision=request.note_revision, upstreamRunIds=request.upstream_run_ids, syntheticDataAttestation=request.synthetic_data_attestation), startedAt=now, completedAt=now, caseResults=(), aggregateMetrics=(), comparison=None, failureSummary=FailureSummary(failedCases=0, invalidOutputCases=0, unscorableCases=0, interruptedCases=0, failureCodes=()))


def _canonicalize_findings(outcome: PipelineOutcome, case, candidate) -> tuple[ObservedFinding, ...]:
    """Map implementation IDs to annotation target IDs after execution.

    The engine receives no annotation records.  This post-processing step only
    joins stable pipeline metadata (claim ordinal/source evidence spans) to the
    dataset's immutable target identifiers so the scorer can perform matching.
    Expected statuses, categories, and error instances are never used here.
    """
    claim_targets = {
        claim_id: candidate.annotated_claims[ordinal - 1].annotated_claim_id
        for claim_id, ordinal in outcome.claim_id_ordinals
        if 1 <= ordinal <= len(candidate.annotated_claims)
    }

    def span_key(span):
        return span.source_id, span.source_version, span.start, span.end

    fact_targets = _source_fact_targets(outcome, case, span_key)

    normalized: list[ObservedFinding] = []
    for finding in outcome.findings:
        normalized.append(finding.model_copy(update={
            "affected_claim_id": claim_targets.get(finding.affected_claim_id, finding.affected_claim_id),
            "affected_source_fact_id": fact_targets.get(finding.affected_source_fact_id, finding.affected_source_fact_id),
        }))
    return tuple(normalized)


def _source_fact_targets(outcome: PipelineOutcome, case, span_key) -> dict[str, str]:
    source_target_by_spans = {
        frozenset(span_key(span) for span in fact.source_spans): fact.source_fact_id
        for fact in case.reference_facts
    }
    return {
        fact_id: target
        for fact_id, spans in outcome.source_fact_spans
        if (target := source_target_by_spans.get(frozenset(span_key(span) for span in spans)))
    }


def _completeness_scores(outcome: PipelineOutcome, findings: tuple[ObservedFinding, ...], case, candidate) -> tuple[SourceFactScore, ...]:
    """Score coverage from engine output, never from expected coverage labels."""
    span_key = lambda span: (span.source_id, span.source_version, span.start, span.end)
    extracted_targets = set(_source_fact_targets(outcome, case, span_key).values())
    scores: list[SourceFactScore] = []
    for fact in case.reference_facts:
        applicable = fact.applicable_to_candidate_ids == "ALL" or candidate.candidate_id in fact.applicable_to_candidate_ids
        if not applicable:
            scores.append(SourceFactScore(sourceFactId=fact.source_fact_id, status="NOT_APPLICABLE", faithfullyCovered=False, matchedClaimIds=()))
            continue
        related = tuple(item for item in findings if item.producer == "SPEC_006" and item.affected_source_fact_id == fact.source_fact_id)
        if any(item.primary_status_or_outcome == "MISSING" for item in related) or fact.source_fact_id not in extracted_targets:
            status = "OMITTED"
        elif related:
            status = "UNCERTAIN"
        else:
            status = "FAITHFULLY_COVERED"
        scores.append(SourceFactScore(
            sourceFactId=fact.source_fact_id,
            status=status,
            faithfullyCovered=status == "FAITHFULLY_COVERED",
            matchedClaimIds=tuple(item.affected_claim_id for item in related if item.affected_claim_id),
        ))
    return tuple(scores)

