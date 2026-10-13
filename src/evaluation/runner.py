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
    FindingMatch, InferenceParameters, LatencyBreakdown, RunConfiguration, RunStatus, SourceFactScore, UsageAndCost,
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
        expected_facts = sum(sum(fact.expectation != "CONTEXTUAL" and (fact.applicable_to_candidate_ids == "ALL" or candidate.candidate_id in fact.applicable_to_candidate_ids) and fact.expected_coverage != "NOT_APPLICABLE" for fact in case.reference_facts) for case in selected for candidate in case.candidate_notes)
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
            matches = match_findings(outcome.findings, candidate.error_instances) if not failure else tuple(FindingMatch(errorId=error.error_id, findingKey=None, disposition="FALSE_NEGATIVE", reasonCode="CASE_FAILED", specificityScore=None) for error in candidate.error_instances)
            scores = tuple(SourceFactScore(sourceFactId=fact.source_fact_id, status="OMITTED" if fact.expected_coverage == "OMITTED" else "FAITHFULLY_COVERED", faithfullyCovered=fact.expected_coverage == "FAITHFULLY_COVERED", matchedClaimIds=tuple(claim.claim_id for claim in candidate.annotated_claims if claim.claim_id)) for fact in case.reference_facts if fact.expected_coverage != "NOT_APPLICABLE")
            return EvaluationCaseResult(caseExecutionId=f"case-{uuid4().hex}", scenarioId=case.scenario_id, candidateId=candidate.candidate_id, sourceId=case.source.source_id, sourceVersion=case.source.source_version, sourceTextHash=case.source.source_text_hash, noteId=candidate.note_id, noteRevision=candidate.note_revision, noteBodyHash=candidate.note_body_hash, status=status, stageRuns=outcome.stage_runs, observedFindings=outcome.findings, matchResults=matches, completenessResults=scores, reviewOutcome=None, latency=LatencyBreakdown(endToEndMilliseconds=outcome.latency_ms or (perf_counter() - started) * 1000), usageAndCost=outcome.usage_and_cost, failure=failure)
        except Exception as error:
            from .contracts import EvaluationFailure
            return EvaluationCaseResult(caseExecutionId=f"case-{uuid4().hex}", scenarioId=case.scenario_id, candidateId=candidate.candidate_id, sourceId=case.source.source_id, sourceVersion=case.source.source_version, sourceTextHash=case.source.source_text_hash, noteId=candidate.note_id, noteRevision=candidate.note_revision, noteBodyHash=candidate.note_body_hash, status=CaseStatus.FAILED, stageRuns=(), observedFindings=(), matchResults=(), completenessResults=(), reviewOutcome=None, latency=LatencyBreakdown(endToEndMilliseconds=(perf_counter() - started) * 1000), usageAndCost=UsageAndCost(retryCount=0, costState="UNAVAILABLE"), failure=EvaluationFailure(code="EVALUATION_ADAPTER_FAILURE", stage=None, retryable=False, message=str(error)))

    def _configuration(self, request) -> RunConfiguration:
        return RunConfiguration(codeVersion=self.code_version, environmentId="local-synthetic", modelProvider=None, modelId=None, modelVersion=None, promptVersionsAndHashes=(), inferenceParameters=InferenceParameters(), ruleVersionsAndRulesetVersions=(), upstreamContractVersions=(
            {"name": "SPEC_004", "version": "EVIDENCE_STATUS-v1"}, {"name": "SPEC_006", "version": "SOURCE_COVERAGE-v1"},
        ), fixtureMode=request.execution_mode, pricingAssumptionsVersion="SYNTHETIC_FIXTURE-v1", matchingPolicyVersion="EVALUATION_MATCHING-v1", randomSeed=0)

    def _invalid_run(self, request, run_id: str, reason: str) -> EvaluationRun:
        now = datetime.now(timezone.utc)
        return EvaluationRun(evaluationRunId=run_id, origin="NEWLY_EXECUTED", runPurpose="BENCHMARK_EVALUATION", scoringState="UNSCORABLE", status=RunStatus.INVALID_DATASET, datasetId=request.dataset_id, datasetVersion=request.dataset_version, datasetHash=request.dataset_hash, selectedSplit=request.selected_split, selectionDigest="invalid", configuration=self._configuration(request), startedAt=now, completedAt=now, caseResults=(), aggregateMetrics=(), comparison=None, failureSummary=FailureSummary(failedCases=0, invalidOutputCases=0, unscorableCases=0, interruptedCases=0, failureCodes=(f"INVALID_DATASET:{reason}",)))

    def _demo_run(self, request, run_id: str) -> EvaluationRun:
        now = datetime.now(timezone.utc)
        from .contracts import DemoInputReference
        return EvaluationRun(evaluationRunId=run_id, origin="NEWLY_EXECUTED", runPurpose="SYNTHETIC_DEMO_TRACKING", scoringState="DEMONSTRATION_ONLY", status=RunStatus.SUCCEEDED, datasetId=None, datasetVersion=None, datasetHash=None, selectedSplit=None, selectionDigest=hashlib.sha256(request.idempotency_key.encode()).hexdigest(), configuration=self._configuration(request), demoReference=DemoInputReference(sourceId=request.source_id, sourceVersion=request.source_version, noteId=request.note_id, noteRevision=request.note_revision, upstreamRunIds=request.upstream_run_ids, syntheticDataAttestation=request.synthetic_data_attestation), startedAt=now, completedAt=now, caseResults=(), aggregateMetrics=(), comparison=None, failureSummary=FailureSummary(failedCases=0, invalidOutputCases=0, unscorableCases=0, interruptedCases=0, failureCodes=()))

