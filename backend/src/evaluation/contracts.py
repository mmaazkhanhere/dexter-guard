from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, str_strip_whitespace=False)


class DatasetSplit(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    HELD_OUT = "HELD_OUT"


class DatasetStatus(StrEnum):
    DRAFT = "DRAFT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    RETIRED = "RETIRED"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    INVALID_DATASET = "INVALID_DATASET"


class CaseStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    UNSCORABLE = "UNSCORABLE"
    SKIPPED = "SKIPPED"


class ResultOrigin(StrEnum):
    HISTORICAL_SAVED_RESULT = "HISTORICAL_SAVED_RESULT"
    NEWLY_EXECUTED = "NEWLY_EXECUTED"


class EvidenceStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNCERTAIN = "UNCERTAIN"


class ErrorCategory(StrEnum):
    UNSUPPORTED_FACT = "UNSUPPORTED_FACT"
    EXPLICIT_CONTRADICTION = "EXPLICIT_CONTRADICTION"
    NUMERIC_MISMATCH = "NUMERIC_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    NEGATION_CHANGE = "NEGATION_CHANGE"
    CERTAINTY_CHANGE = "CERTAINTY_CHANGE"
    ATTRIBUTION_CHANGE = "ATTRIBUTION_CHANGE"
    CLINICAL_INFERENCE = "CLINICAL_INFERENCE"
    IMPORTANT_OMISSION = "IMPORTANT_OMISSION"
    OTHER = "OTHER"


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class MatchDisposition(StrEnum):
    MATCHED = "MATCHED"
    DUPLICATE = "DUPLICATE"
    UNMATCHED_WARNING = "UNMATCHED_WARNING"
    TARGET_LINKED_MISCLASSIFICATION = "TARGET_LINKED_MISCLASSIFICATION"
    FALSE_NEGATIVE = "FALSE_NEGATIVE"
    UNSCORABLE = "UNSCORABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MetricState(StrEnum):
    SCORED = "SCORED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"


class ComparisonStatus(StrEnum):
    VALID = "VALID"
    INVALID_PAIR = "INVALID_PAIR"
    NOT_RUN = "NOT_RUN"
    SIMULATED = "SIMULATED"


class ReviewDataKind(StrEnum):
    OBSERVED = "OBSERVED"
    SIMULATED = "SIMULATED"
    UNAVAILABLE = "UNAVAILABLE"


class SourceSpan(Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(ge=1)

    @model_validator(mode="after")
    def non_empty(self) -> "SourceSpan":
        if self.end <= self.start:
            raise ValueError("source span must be non-empty")
        return self


class SourceSnapshotReference(Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    source_text_hash: StrictStr = Field(alias="sourceTextHash", pattern=r"^[a-f0-9]{64}$")
    resident_test_id: StrictStr = Field(alias="residentTestId", min_length=1)
    language: Literal["de-DE"]
    transcript_locator: StrictStr = Field(alias="transcriptLocator", min_length=1)
    transcript_text: StrictStr = Field(alias="transcriptText", min_length=1)


class AnnotatedSourceFact(Contract):
    source_fact_id: StrictStr = Field(alias="sourceFactId", min_length=1)
    source_spans: tuple[SourceSpan, ...] = Field(alias="sourceSpans", min_length=1)
    expectation: Literal["REQUIRED", "IMPORTANT", "CONTEXTUAL"]
    applicable_to_candidate_ids: tuple[StrictStr, ...] | Literal["ALL"] = Field(alias="applicableToCandidateIds")
    expected_evidence_relationship: StrictStr = Field(alias="expectedEvidenceRelationship", min_length=1)
    expected_coverage: Literal["FAITHFULLY_COVERED", "OMITTED", "NOT_APPLICABLE"] = Field(alias="expectedCoverage")


class AnnotationProvenance(Contract):
    annotator_label: StrictStr = Field(alias="annotatorLabel", min_length=1)
    annotated_at: datetime = Field(alias="annotatedAt")
    review_status: Literal["INDEPENDENTLY_REVIEWED", "DISPUTED", "PENDING"] = Field(alias="reviewStatus")
    guide_version: StrictStr = Field(alias="guideVersion", min_length=1)
    disagreements: tuple[StrictStr, ...] = ()
    resolution_id: StrictStr | None = Field(default=None, alias="resolutionId")
    rationale_locator: StrictStr | None = Field(default=None, alias="rationaleLocator")


class AnnotatedCandidateClaim(Contract):
    annotated_claim_id: StrictStr = Field(alias="annotatedClaimId", min_length=1)
    claim_id: StrictStr | None = Field(default=None, alias="claimId")
    statement_reference: StrictStr = Field(alias="statementReference", min_length=1)
    expected_primary_status: EvidenceStatus = Field(alias="expectedPrimaryStatus")
    expected_discrepancies: tuple[StrictStr, ...] = Field(alias="expectedDiscrepancies")
    expected_evidence_spans: tuple[SourceSpan, ...] = Field(alias="expectedEvidenceSpans")
    scorable: StrictBool


class GroundTruthError(Contract):
    error_id: StrictStr = Field(alias="errorId", min_length=1)
    candidate_id: StrictStr = Field(alias="candidateId", min_length=1)
    affected_annotated_claim_id: StrictStr | None = Field(default=None, alias="affectedAnnotatedClaimId")
    affected_source_fact_id: StrictStr | None = Field(default=None, alias="affectedSourceFactId")
    category: ErrorCategory
    severity: Severity
    expected_primary_status: EvidenceStatus | None = Field(default=None, alias="expectedPrimaryStatus")
    required_discrepancy_or_rule: StrictStr | None = Field(default=None, alias="requiredDiscrepancyOrRule")
    conflicting_attribute: StrictStr | None = Field(default=None, alias="conflictingAttribute")
    expected_value: StrictStr | None = Field(default=None, alias="expectedValue")
    source_evidence_spans: tuple[SourceSpan, ...] = Field(alias="sourceEvidenceSpans")
    applicable: StrictBool

    @model_validator(mode="after")
    def exactly_one_target(self) -> "GroundTruthError":
        if (self.affected_annotated_claim_id is None) == (self.affected_source_fact_id is None):
            raise ValueError("ground-truth error must have exactly one affected target")
        return self


class EvaluationCandidate(Contract):
    candidate_id: StrictStr = Field(alias="candidateId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    note_body_hash: StrictStr = Field(alias="noteBodyHash", pattern=r"^[a-f0-9]{64}$")
    note_body: StrictStr = Field(alias="noteBody", min_length=1)
    origin: Literal["GENERATED", "EXTERNALLY_SUPPLIED", "FIXTURE"]
    annotated_claims: tuple[AnnotatedCandidateClaim, ...] = Field(alias="annotatedClaims")
    error_instances: tuple[GroundTruthError, ...] = Field(alias="errorInstances")


class EvaluationCase(Contract):
    scenario_id: StrictStr = Field(alias="scenarioId", min_length=1)
    scenario_family_id: StrictStr = Field(alias="scenarioFamilyId", min_length=1)
    dataset_version: StrictStr = Field(alias="datasetVersion", min_length=1)
    split: DatasetSplit
    tags: tuple[StrictStr, ...] = Field(min_length=1)
    source: SourceSnapshotReference
    reference_facts: tuple[AnnotatedSourceFact, ...] = Field(alias="referenceFacts")
    candidate_notes: tuple[EvaluationCandidate, ...] = Field(alias="candidateNotes", min_length=1)
    annotation_provenance: AnnotationProvenance = Field(alias="annotationProvenance")


class BenchmarkDataset(Contract):
    dataset_id: StrictStr = Field(alias="datasetId", min_length=1)
    dataset_version: StrictStr = Field(alias="datasetVersion", min_length=1)
    content_hash: StrictStr = Field(alias="contentHash", pattern=r"^[a-f0-9]{64}$")
    status: DatasetStatus
    language: Literal["de-DE"]
    scenario_count: StrictInt = Field(alias="scenarioCount", ge=0)
    annotation_guide_version: StrictStr = Field(alias="annotationGuideVersion", min_length=1)
    evidence_status_policy_version: Literal["EVIDENCE_STATUS-v1"] = Field(alias="evidenceStatusPolicyVersion")
    annotation_policy_version: Literal["EVIDENCE_ANNOTATION-v1"] = Field(alias="annotationPolicyVersion")
    matching_policy_version: Literal["EVALUATION_MATCHING-v1"] = Field(alias="matchingPolicyVersion")
    created_at: datetime = Field(alias="createdAt")
    accepted_at: datetime | None = Field(default=None, alias="acceptedAt")
    scenarios: tuple[EvaluationCase, ...]

    def canonical_content(self) -> str:
        import json
        payload = self.model_dump(mode="json", by_alias=True, exclude={"content_hash"})
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class VersionedValue(Contract):
    name: StrictStr = Field(min_length=1)
    version: StrictStr = Field(min_length=1)
    hash: StrictStr | None = None


class InferenceParameters(Contract):
    temperature: StrictFloat | None = None
    top_p: StrictFloat | None = Field(default=None, alias="topP")
    max_tokens: StrictInt | None = Field(default=None, alias="maxTokens")
    timeout_seconds: StrictFloat | None = Field(default=None, alias="timeoutSeconds")
    retry_limit: StrictInt | None = Field(default=None, alias="retryLimit")
    seed: StrictInt | None = None


class RunConfiguration(Contract):
    code_version: StrictStr = Field(alias="codeVersion", min_length=1)
    environment_id: StrictStr = Field(alias="environmentId", min_length=1)
    model_provider: StrictStr | None = Field(default=None, alias="modelProvider")
    model_id: StrictStr | None = Field(default=None, alias="modelId")
    model_version: StrictStr | None = Field(default=None, alias="modelVersion")
    prompt_versions_and_hashes: tuple[VersionedValue, ...] = Field(alias="promptVersionsAndHashes")
    inference_parameters: InferenceParameters = Field(alias="inferenceParameters")
    rule_versions_and_ruleset_versions: tuple[VersionedValue, ...] = Field(alias="ruleVersionsAndRulesetVersions")
    upstream_contract_versions: tuple[VersionedValue, ...] = Field(alias="upstreamContractVersions")
    fixture_mode: Literal["LIVE", "SAVED_FIXTURE", "MOCKED_PROVIDER"] = Field(alias="fixtureMode")
    pricing_assumptions_version: StrictStr | None = Field(default=None, alias="pricingAssumptionsVersion")
    matching_policy_version: Literal["EVALUATION_MATCHING-v1"] = Field(alias="matchingPolicyVersion")
    random_seed: StrictInt | None = Field(default=None, alias="randomSeed")


class DemoInputReference(Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    upstream_run_ids: tuple[StrictStr, ...] = Field(alias="upstreamRunIds", min_length=1)
    synthetic_data_attestation: StrictStr = Field(alias="syntheticDataAttestation", min_length=1)


class EvaluationRunRequest(Contract):
    subject_kind: Literal["BENCHMARK", "SYNTHETIC_DEMO"] = Field(alias="subjectKind")
    execution_mode: Literal["LIVE", "SAVED_FIXTURE", "MOCKED_PROVIDER"] = Field(alias="executionMode")
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
    dataset_id: StrictStr | None = Field(default=None, alias="datasetId")
    dataset_version: StrictStr | None = Field(default=None, alias="datasetVersion")
    dataset_hash: StrictStr | None = Field(default=None, alias="datasetHash")
    selected_split: DatasetSplit | None = Field(default=None, alias="selectedSplit")
    reference_run_id: StrictStr | None = Field(default=None, alias="referenceRunId")
    source_id: StrictStr | None = Field(default=None, alias="sourceId")
    source_version: StrictInt | None = Field(default=None, alias="sourceVersion")
    note_id: StrictStr | None = Field(default=None, alias="noteId")
    note_revision: StrictInt | None = Field(default=None, alias="noteRevision")
    upstream_run_ids: tuple[StrictStr, ...] = Field(default=(), alias="upstreamRunIds")
    synthetic_data_attestation: StrictStr | None = Field(default=None, alias="syntheticDataAttestation")

    @model_validator(mode="after")
    def request_shape(self) -> "EvaluationRunRequest":
        if self.subject_kind == "BENCHMARK":
            if not all((self.dataset_id, self.dataset_version, self.dataset_hash, self.selected_split)):
                raise ValueError("benchmark requests require dataset identity and explicit selectedSplit")
            if any(value is not None for value in (self.source_id, self.note_id, self.synthetic_data_attestation)):
                raise ValueError("benchmark request cannot contain demo references")
        else:
            if self.execution_mode != "LIVE" or not all((self.source_id, self.source_version, self.note_id, self.note_revision, self.synthetic_data_attestation)) or not self.upstream_run_ids:
                raise ValueError("synthetic demo requests require immutable upstream references and LIVE mode")
            if any(value is not None for value in (self.dataset_id, self.dataset_version, self.dataset_hash, self.selected_split)):
                raise ValueError("demo request cannot contain benchmark selection")
        return self


class StageRunReference(Contract):
    stage: Literal["CLAIM_EXTRACTION", "EVIDENCE_VERIFICATION", "DETERMINISTIC_VALIDATION", "SOURCE_COVERAGE", "HUMAN_REVIEW"]
    upstream_run_id: StrictStr = Field(alias="upstreamRunId", min_length=1)
    status: StrictStr = Field(min_length=1)


class ObservedFinding(Contract):
    finding_key: StrictStr = Field(alias="findingKey", min_length=1)
    producer: Literal["SPEC_004", "SPEC_005", "SPEC_006", "REVIEW_OPERATIONAL"]
    upstream_run_id: StrictStr = Field(alias="upstreamRunId", min_length=1)
    affected_claim_id: StrictStr | None = Field(default=None, alias="affectedClaimId")
    affected_source_fact_id: StrictStr | None = Field(default=None, alias="affectedSourceFactId")
    primary_status_or_outcome: StrictStr = Field(alias="primaryStatusOrOutcome", min_length=1)
    discrepancy_or_rule: StrictStr | None = Field(default=None, alias="discrepancyOrRule")
    conflicting_attribute_or_value: StrictStr | None = Field(default=None, alias="conflictingAttributeOrValue")
    source_spans: tuple[SourceSpan, ...] = Field(alias="sourceSpans")
    requires_correction_or_review: StrictBool = Field(alias="requiresCorrectionOrReview")


class FindingMatch(Contract):
    error_id: StrictStr = Field(alias="errorId", min_length=1)
    finding_key: StrictStr | None = Field(default=None, alias="findingKey")
    disposition: MatchDisposition
    reason_code: StrictStr = Field(alias="reasonCode", min_length=1)
    specificity_score: StrictInt | None = Field(default=None, alias="specificityScore", ge=0)


class SourceFactScore(Contract):
    source_fact_id: StrictStr = Field(alias="sourceFactId", min_length=1)
    status: Literal["FAITHFULLY_COVERED", "OMITTED", "NOT_APPLICABLE", "UNCERTAIN"]
    faithfully_covered: StrictBool = Field(alias="faithfullyCovered")
    matched_claim_ids: tuple[StrictStr, ...] = Field(alias="matchedClaimIds")


class ReviewOutcome(Contract):
    data_kind: ReviewDataKind = Field(alias="dataKind")
    final_revision: StrictInt | None = Field(default=None, alias="finalRevision")
    remaining_error_count: StrictInt = Field(alias="remainingErrorCount", ge=0)
    remaining_omission_count: StrictInt = Field(alias="remainingOmissionCount", ge=0)
    warning_count: StrictInt = Field(alias="warningCount", ge=0)
    human_decision_count: StrictInt = Field(alias="humanDecisionCount", ge=0)
    correction_action_count: StrictInt = Field(alias="correctionActionCount", ge=0)


class LatencyBreakdown(Contract):
    end_to_end_milliseconds: StrictFloat | None = Field(default=None, alias="endToEndMilliseconds")
    stage_milliseconds: dict[str, StrictFloat | None] = Field(default_factory=dict, alias="stageMilliseconds")


class UsageAndCost(Contract):
    input_tokens: StrictInt | None = Field(default=None, alias="inputTokens")
    output_tokens: StrictInt | None = Field(default=None, alias="outputTokens")
    retry_count: StrictInt = Field(alias="retryCount", ge=0)
    cost_state: Literal["AVAILABLE", "UNAVAILABLE"] = Field(alias="costState")
    estimated_cost: StrictFloat | None = Field(default=None, alias="estimatedCost")
    currency: StrictStr | None = None
    pricing_assumptions_version: StrictStr | None = Field(default=None, alias="pricingAssumptionsVersion")


class EvaluationFailure(Contract):
    code: StrictStr = Field(min_length=1)
    stage: StrictStr | None = None
    retryable: StrictBool
    message: StrictStr = Field(min_length=1)


class FailureSummary(Contract):
    failed_cases: StrictInt = Field(alias="failedCases", ge=0)
    invalid_output_cases: StrictInt = Field(alias="invalidOutputCases", ge=0)
    unscorable_cases: StrictInt = Field(alias="unscorableCases", ge=0)
    interrupted_cases: StrictInt = Field(alias="interruptedCases", ge=0)
    failure_codes: tuple[StrictStr, ...] = Field(alias="failureCodes")


class EvaluationCaseResult(Contract):
    case_execution_id: StrictStr = Field(alias="caseExecutionId", min_length=1)
    scenario_id: StrictStr = Field(alias="scenarioId", min_length=1)
    candidate_id: StrictStr = Field(alias="candidateId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    source_text_hash: StrictStr = Field(alias="sourceTextHash", pattern=r"^[a-f0-9]{64}$")
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    note_body_hash: StrictStr = Field(alias="noteBodyHash", pattern=r"^[a-f0-9]{64}$")
    status: CaseStatus
    stage_runs: tuple[StageRunReference, ...] = Field(alias="stageRuns")
    observed_findings: tuple[ObservedFinding, ...] = Field(alias="observedFindings")
    match_results: tuple[FindingMatch, ...] = Field(alias="matchResults")
    completeness_results: tuple[SourceFactScore, ...] = Field(alias="completenessResults")
    review_outcome: ReviewOutcome | None = Field(default=None, alias="reviewOutcome")
    latency: LatencyBreakdown
    usage_and_cost: UsageAndCost = Field(alias="usageAndCost")
    failure: EvaluationFailure | None = None


class ConfidenceInterval(Contract):
    method: StrictStr
    level: StrictFloat
    lower: StrictFloat
    upper: StrictFloat


class MetricCommon(Contract):
    metric_id: StrictStr = Field(alias="metricId", min_length=1)
    metric_kind: Literal["RATE", "COUNT_PER_NOTE", "DURATION_DISTRIBUTION", "COST_DISTRIBUTION"] = Field(alias="metricKind")
    state: MetricState
    scorable_count: StrictInt = Field(alias="scorableCount", ge=0)
    unscorable_count: StrictInt = Field(alias="unscorableCount", ge=0)
    failed_count: StrictInt = Field(alias="failedCount", ge=0)
    aggregation_method: StrictStr = Field(alias="aggregationMethod", min_length=1)
    policy_version: Literal["EVALUATION_METRICS-v1"] = Field(alias="policyVersion")
    reason: StrictStr | None = None


class RateMetric(MetricCommon):
    metric_kind: Literal["RATE"] = Field(alias="metricKind")
    numerator: StrictInt = Field(ge=0)
    denominator: StrictInt = Field(ge=0)
    value: StrictFloat | None = None
    confidence_interval: ConfidenceInterval | None = Field(default=None, alias="confidenceInterval")


class CountMetric(MetricCommon):
    metric_kind: Literal["COUNT_PER_NOTE"] = Field(alias="metricKind")
    count: StrictInt = Field(ge=0)
    note_count: StrictInt = Field(alias="noteCount", ge=0)
    value_per_note: StrictFloat | None = Field(default=None, alias="valuePerNote")
    unit: Literal[
        "WARNINGS", "HUMAN_DECISIONS", "CORRECTION_ACTIONS", "ERRORS", "NOTES",
        "TRUE_POSITIVES", "FALSE_POSITIVES", "FALSE_NEGATIVES",
    ]


class DistributionMetric(MetricCommon):
    metric_kind: Literal["DURATION_DISTRIBUTION", "COST_DISTRIBUTION"] = Field(alias="metricKind")
    observation_count: StrictInt = Field(alias="observationCount", ge=0)
    p50: StrictFloat | None = None
    p95: StrictFloat | None = None
    mean: StrictFloat | None = None
    unit: Literal["MILLISECONDS", "CURRENCY_PER_NOTE"]
    currency: StrictStr | None = None
    confidence_interval: ConfidenceInterval | None = Field(default=None, alias="confidenceInterval")


MetricResult = RateMetric | CountMetric | DistributionMetric


class PairResult(Contract):
    scenario_id: StrictStr = Field(alias="scenarioId", min_length=1)
    candidate_id: StrictStr = Field(alias="candidateId", min_length=1)
    candidate_body_hash: StrictStr = Field(alias="candidateBodyHash", min_length=1)
    baseline_case_execution_id: StrictStr = Field(alias="baselineCaseExecutionId", min_length=1)
    validated_case_execution_id: StrictStr = Field(alias="validatedCaseExecutionId", min_length=1)
    status: Literal["VALID", "INVALID_PAIR"]
    invalid_reason: StrictStr | None = Field(default=None, alias="invalidReason")


class MetricDelta(Contract):
    metric_id: StrictStr = Field(alias="metricId", min_length=1)
    baseline_value: StrictFloat | None = Field(default=None, alias="baselineValue")
    validated_value: StrictFloat | None = Field(default=None, alias="validatedValue")
    delta: StrictFloat | None = None
    confidence_interval: ConfidenceInterval | None = Field(default=None, alias="confidenceInterval")


class RunComparison(Contract):
    comparison_id: StrictStr = Field(alias="comparisonId", min_length=1)
    status: ComparisonStatus
    baseline_run_id: StrictStr = Field(alias="baselineRunId", min_length=1)
    validated_run_id: StrictStr = Field(alias="validatedRunId", min_length=1)
    pair_results: tuple[PairResult, ...] = Field(alias="pairResults")
    review_data_kind: ReviewDataKind = Field(alias="reviewDataKind")
    simulation_policy_version: StrictStr | None = Field(default=None, alias="simulationPolicyVersion")
    aggregate_deltas: tuple[MetricDelta, ...] = Field(alias="aggregateDeltas")


class EvaluationRun(Contract):
    evaluation_run_id: StrictStr = Field(alias="evaluationRunId", min_length=1)
    origin: ResultOrigin
    run_purpose: Literal["BENCHMARK_EVALUATION", "SYNTHETIC_DEMO_TRACKING"] = Field(alias="runPurpose")
    scoring_state: Literal["SCORED", "DEMONSTRATION_ONLY", "UNSCORABLE"] = Field(alias="scoringState")
    status: RunStatus
    dataset_id: StrictStr | None = Field(default=None, alias="datasetId")
    dataset_version: StrictStr | None = Field(default=None, alias="datasetVersion")
    dataset_hash: StrictStr | None = Field(default=None, alias="datasetHash")
    selected_split: DatasetSplit | None = Field(default=None, alias="selectedSplit")
    selection_digest: StrictStr = Field(alias="selectionDigest", min_length=1)
    configuration: RunConfiguration
    demo_reference: DemoInputReference | None = Field(default=None, alias="demoReference")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    case_results: tuple[EvaluationCaseResult, ...] = Field(alias="caseResults")
    aggregate_metrics: tuple[RateMetric | CountMetric | DistributionMetric, ...] = Field(alias="aggregateMetrics")
    comparison: RunComparison | None = None
    failure_summary: FailureSummary = Field(alias="failureSummary")
    report_schema_version: Literal["EVALUATION_REPORT-v1"] = Field(default="EVALUATION_REPORT-v1", alias="reportSchemaVersion")
    results_immutable: StrictBool = Field(default=True, alias="resultsImmutable")

