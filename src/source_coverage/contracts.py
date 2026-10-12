"""Versioned Pydantic contracts for source coverage verification."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator


CONTRACT_VERSION = "COVERAGE-CONTRACT-v1"
STATUS_POLICY_VERSION = "COVERAGE_STATUS-v1"
EXPECTATION_POLICY_VERSION = "COVERAGE_EXPECTATION-v1"
RULESET_VERSION = "COVERAGE-RULESET-v1"


class _Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=False,
    )


class SourceFactCategory(StrEnum):
    SYMPTOM = "SYMPTOM"
    MEASUREMENT = "MEASUREMENT"
    MOBILITY = "MOBILITY"
    CARE_ACTION = "CARE_ACTION"
    OBSERVATION = "OBSERVATION"
    OTHER = "OTHER"


class DocumentationExpectation(StrEnum):
    REQUIRED = "REQUIRED"
    IMPORTANT = "IMPORTANT"
    CONTEXTUAL = "CONTEXTUAL"


class CoverageStatus(StrEnum):
    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    MISSING = "MISSING"
    DISTORTED = "DISTORTED"
    UNCERTAIN = "UNCERTAIN"


class RunStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class MaterialAttribute(StrEnum):
    SUBJECT = "SUBJECT"
    POLARITY = "POLARITY"
    CERTAINTY = "CERTAINTY"
    ATTRIBUTION = "ATTRIBUTION"
    TEMPORAL = "TEMPORAL"
    LATERALITY = "LATERALITY"
    NUMERIC_VALUE = "NUMERIC_VALUE"
    UNIT = "UNIT"
    APPROXIMATION = "APPROXIMATION"
    MOBILITY_ASSISTANCE = "MOBILITY_ASSISTANCE"
    CARE_ACTION = "CARE_ACTION"
    OTHER = "OTHER"


class Polarity(StrEnum):
    AFFIRMED = "AFFIRMED"
    NEGATED = "NEGATED"
    UNKNOWN = "UNKNOWN"


class Certainty(StrEnum):
    CERTAIN = "CERTAIN"
    UNCERTAIN = "UNCERTAIN"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


class Attribution(StrEnum):
    CARE_RECIPIENT = "CARE_RECIPIENT"
    CAREGIVER = "CAREGIVER"
    THIRD_PARTY = "THIRD_PARTY"
    DOCUMENT_AUTHOR = "DOCUMENT_AUTHOR"
    UNSPECIFIED = "UNSPECIFIED"


class Laterality(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BILATERAL = "BILATERAL"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class Approximation(StrEnum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    UNKNOWN = "UNKNOWN"


class SourceSpan(_Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(ge=1)

    @model_validator(mode="after")
    def require_non_empty_range(self) -> "SourceSpan":
        if self.end <= self.start:
            raise ValueError("source span must be non-empty and end-exclusive")
        return self


class ResidentContextReference(_Contract):
    resident_test_id: StrictStr = Field(alias="residentTestId", min_length=1)
    source: Literal["SPEC_001_SOURCE_DOCUMENT"]
    trust_level: Literal["AUTHORITATIVE_TRANSCRIPT"] = Field(alias="trustLevel")
    version: StrictStr = Field(min_length=1)
    permitted_use: Literal["TRANSCRIPT_EVIDENCE_ONLY"] = Field(alias="permittedUse")


class SourceFact(_Contract):
    source_fact_id: StrictStr = Field(alias="sourceFactId", min_length=1)
    source_fact_extraction_run_id: StrictStr = Field(alias="sourceFactExtractionRunId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    resident_context: ResidentContextReference = Field(alias="residentContext")
    source_text_hash: StrictStr = Field(alias="sourceTextHash", pattern=r"^[a-f0-9]{64}$")
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)
    category: SourceFactCategory
    fact_text: StrictStr = Field(alias="factText", min_length=1)
    subject: StrictStr | None = Field(default=None, min_length=1)
    polarity: Polarity
    certainty: Certainty
    attribution: Attribution
    temporal_text: StrictStr | None = Field(default=None, alias="temporalText", min_length=1)
    laterality: Laterality
    numeric_value: StrictStr | None = Field(default=None, alias="numericValue", min_length=1)
    unit: StrictStr | None = Field(default=None, min_length=1)
    approximation: Approximation
    mobility_assistance: StrictStr | None = Field(default=None, alias="mobilityAssistance", min_length=1)
    care_action: StrictStr | None = Field(default=None, alias="careAction", min_length=1)
    documentation_expectation: DocumentationExpectation = Field(alias="documentationExpectation")
    severity_policy_key: StrictStr | None = Field(default=None, alias="severityPolicyKey", min_length=1)
    source_spans: tuple[SourceSpan, ...] = Field(alias="sourceSpans", min_length=1)

    @model_validator(mode="after")
    def validate_policy_and_identity(self) -> "SourceFact":
        if self.documentation_expectation is DocumentationExpectation.CONTEXTUAL and self.severity_policy_key:
            raise ValueError("contextual facts cannot have a severity policy key")
        if (self.numeric_value is None) != (self.unit is None):
            raise ValueError("numeric_value and unit must be supplied together")
        if any((span.source_id, span.source_version) != (self.source_id, self.source_version) for span in self.source_spans):
            raise ValueError("all source spans must match the source fact identity")
        return self


class UnresolvedSourceItem(_Contract):
    unresolved_source_item_id: StrictStr = Field(alias="unresolvedSourceItemId", min_length=1)
    source_fact_extraction_run_id: StrictStr = Field(alias="sourceFactExtractionRunId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    resident_context: ResidentContextReference = Field(alias="residentContext")
    source_text_hash: StrictStr = Field(alias="sourceTextHash", pattern=r"^[a-f0-9]{64}$")
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)
    candidate_source_spans: tuple[SourceSpan, ...] = Field(alias="candidateSourceSpans", min_length=1)
    explanation: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def validate_span_identity(self) -> "UnresolvedSourceItem":
        if any((span.source_id, span.source_version) != (self.source_id, self.source_version) for span in self.candidate_source_spans):
            raise ValueError("all unresolved spans must match the source identity")
        return self


class RelatedFindingRef(_Contract):
    owner: Literal["SPEC_004", "SPEC_005"]
    finding_id: StrictStr = Field(alias="findingId", min_length=1)


class SemanticRelationKind(StrEnum):
    FAITHFUL = "FAITHFUL"
    RELATED_ATTRIBUTE_OMITTED = "RELATED_ATTRIBUTE_OMITTED"
    RELATED_ATTRIBUTE_DISTORTED = "RELATED_ATTRIBUTE_DISTORTED"
    UNRESOLVED = "UNRESOLVED"
    NOT_RELATED = "NOT_RELATED"


class SemanticRelation(_Contract):
    source_fact_id: StrictStr = Field(alias="sourceFactId", min_length=1)
    claim_id: StrictStr | None = Field(default=None, alias="claimId", min_length=1)
    kind: SemanticRelationKind
    preserved_attributes: tuple[MaterialAttribute, ...] = Field(alias="preservedAttributes")
    missing_attributes: tuple[MaterialAttribute, ...] = Field(alias="missingAttributes")
    distorted_attributes: tuple[MaterialAttribute, ...] = Field(alias="distortedAttributes")
    explanation: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def require_claim_for_comparison(self) -> "SemanticRelation":
        if self.kind is not SemanticRelationKind.NOT_RELATED and self.claim_id is None:
            raise ValueError("non-NOT_RELATED relations require claim_id")
        return self


class CoverageAssessment(_Contract):
    assessment_id: StrictStr = Field(alias="assessmentId", min_length=1)
    source_fact_id: StrictStr | None = Field(default=None, alias="sourceFactId", min_length=1)
    unresolved_source_item_id: StrictStr | None = Field(default=None, alias="unresolvedSourceItemId", min_length=1)
    status: CoverageStatus
    source_spans: tuple[SourceSpan, ...] = Field(alias="sourceSpans", min_length=1)
    source_quotes: tuple[StrictStr, ...] = Field(alias="sourceQuotes", min_length=1)
    matched_claim_ids: tuple[StrictStr, ...] = Field(alias="matchedClaimIds")
    preserved_attributes: tuple[MaterialAttribute, ...] = Field(alias="preservedAttributes")
    missing_attributes: tuple[MaterialAttribute, ...] = Field(alias="missingAttributes")
    distorted_attributes: tuple[MaterialAttribute, ...] = Field(alias="distortedAttributes")
    explanation: StrictStr = Field(min_length=1)
    related_finding_refs: tuple[RelatedFindingRef, ...] = Field(alias="relatedFindingRefs")

    @model_validator(mode="after")
    def validate_closure(self) -> "CoverageAssessment":
        if (self.source_fact_id is None) == (self.unresolved_source_item_id is None):
            raise ValueError("an assessment must identify exactly one source fact or unresolved item")
        if self.status is CoverageStatus.COVERED:
            if not self.matched_claim_ids or self.missing_attributes or self.distorted_attributes:
                raise ValueError("COVERED requires a faithful matched claim and no differences")
        elif self.status is CoverageStatus.PARTIALLY_COVERED:
            if not self.matched_claim_ids or not self.missing_attributes or self.distorted_attributes:
                raise ValueError("PARTIALLY_COVERED requires missing attributes only")
        elif self.status is CoverageStatus.MISSING:
            if self.matched_claim_ids or self.distorted_attributes:
                raise ValueError("MISSING cannot have matched claims or distorted attributes")
        elif self.status is CoverageStatus.DISTORTED:
            if not self.matched_claim_ids or not self.distorted_attributes or self.missing_attributes:
                raise ValueError("DISTORTED requires distorted attributes only")
        elif self.status is CoverageStatus.UNCERTAIN and self.unresolved_source_item_id is not None and self.matched_claim_ids:
            raise ValueError("unresolved source items cannot have matched claims")
        return self


class CoverageFinding(_Contract):
    coverage_finding_id: StrictStr = Field(alias="coverageFindingId", min_length=1)
    assessment_id: StrictStr = Field(alias="assessmentId", min_length=1)
    source_fact_id: StrictStr | None = Field(default=None, alias="sourceFactId", min_length=1)
    unresolved_source_item_id: StrictStr | None = Field(default=None, alias="unresolvedSourceItemId", min_length=1)
    status: Literal[CoverageStatus.PARTIALLY_COVERED, CoverageStatus.MISSING, CoverageStatus.DISTORTED, CoverageStatus.UNCERTAIN]
    coverage_status_policy_version: Literal[STATUS_POLICY_VERSION] = Field(alias="coverageStatusPolicyVersion")
    expectation_policy_version: Literal[EXPECTATION_POLICY_VERSION] = Field(alias="expectationPolicyVersion")
    ruleset_version: Literal[RULESET_VERSION] = Field(alias="rulesetVersion")
    documentation_expectation: DocumentationExpectation | None = Field(default=None, alias="documentationExpectation")
    severity_policy_key: StrictStr | None = Field(default=None, alias="severityPolicyKey", min_length=1)
    source_spans: tuple[SourceSpan, ...] = Field(alias="sourceSpans", min_length=1)
    source_quotes: tuple[StrictStr, ...] = Field(alias="sourceQuotes", min_length=1)
    matched_claim_ids: tuple[StrictStr, ...] = Field(alias="matchedClaimIds")
    missing_attributes: tuple[MaterialAttribute, ...] = Field(alias="missingAttributes")
    distorted_attributes: tuple[MaterialAttribute, ...] = Field(alias="distortedAttributes")
    suggestion: StrictStr = Field(min_length=1)
    related_finding_refs: tuple[RelatedFindingRef, ...] = Field(alias="relatedFindingRefs")
    requires_review: Literal[True] = Field(alias="requiresReview")

    @model_validator(mode="after")
    def validate_owner(self) -> "CoverageFinding":
        if (self.source_fact_id is None) == (self.unresolved_source_item_id is None):
            raise ValueError("a finding must identify exactly one source fact or unresolved item")
        if self.status is CoverageStatus.MISSING and self.matched_claim_ids:
            raise ValueError("MISSING finding cannot have matched claims")
        return self


class CoverageCounts(_Contract):
    extracted_expected_facts: StrictInt = Field(alias="extractedExpectedFacts", ge=0)
    covered_expected_facts: StrictInt = Field(alias="coveredExpectedFacts", ge=0)
    partially_covered_expected_facts: StrictInt = Field(alias="partiallyCoveredExpectedFacts", ge=0)
    missing_expected_facts: StrictInt = Field(alias="missingExpectedFacts", ge=0)
    distorted_expected_facts: StrictInt = Field(alias="distortedExpectedFacts", ge=0)
    uncertain_expected_facts: StrictInt = Field(alias="uncertainExpectedFacts", ge=0)
    unresolved_source_items: StrictInt = Field(alias="unresolvedSourceItems", ge=0)
    unresolved_source_items_require_review: Literal[True] = Field(alias="unresolvedSourceItemsRequireReview")
    runtime_completeness: float | None = Field(alias="runtimeCompleteness", ge=0, le=1)
    metric_basis: Literal["SYSTEM_EXTRACTED_EXPECTED_FACTS"] = Field(alias="metricBasis")

    @model_validator(mode="after")
    def validate_counts(self) -> "CoverageCounts":
        total = (
            self.covered_expected_facts
            + self.partially_covered_expected_facts
            + self.missing_expected_facts
            + self.distorted_expected_facts
            + self.uncertain_expected_facts
        )
        if total != self.extracted_expected_facts:
            raise ValueError("coverage status counts must equal extracted expected facts")
        expected = self.covered_expected_facts / self.extracted_expected_facts if self.extracted_expected_facts else None
        if self.runtime_completeness != expected:
            raise ValueError("runtime completeness must be covered divided by extracted expected facts")
        return self


class ExecutionMetrics(_Contract):
    latency_milliseconds: StrictInt = Field(alias="latencyMilliseconds", ge=0)
    retry_count: StrictInt = Field(alias="retryCount", ge=0)
    input_tokens: StrictInt | None = Field(default=None, alias="inputTokens", ge=0)
    output_tokens: StrictInt | None = Field(default=None, alias="outputTokens", ge=0)
    inference_cost: float | None = Field(default=None, alias="inferenceCost", ge=0)
    warning_count: StrictInt = Field(alias="warningCount", ge=0)


class Failure(_Contract):
    code: Literal[
        "MALFORMED_PROVIDER_OUTPUT", "PROVIDER_TIMEOUT", "INVALID_SOURCE_SPAN", "PROVENANCE_CONFLICT",
        "MISSING_ASSESSMENT", "IDEMPOTENCY_KEY_CONFLICT", "DEPENDENCY_UNAVAILABLE", "INTERNAL_ERROR",
    ]
    message: StrictStr = Field(min_length=1)
    retryable: StrictBool


class CoverageRunRequest(_Contract):
    contract_version: Literal[CONTRACT_VERSION] = Field(alias="contractVersion")
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    resident_context: ResidentContextReference = Field(alias="residentContext")
    source_text_hash: StrictStr = Field(alias="sourceTextHash", pattern=r"^[a-f0-9]{64}$")
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    source_fact_extraction_run_id: StrictStr = Field(alias="sourceFactExtractionRunId", min_length=1)
    claim_set_id: StrictStr = Field(alias="claimSetId", min_length=1)
    ruleset_version: Literal[RULESET_VERSION] = Field(alias="rulesetVersion")
    dataset_version: StrictStr = Field(alias="datasetVersion", min_length=1)
    related_finding_run_ids: tuple[StrictStr, ...] = Field(default=(), alias="relatedFindingRunIds")
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)


class _RunBase(_Contract):
    coverage_run_id: StrictStr = Field(alias="coverageRunId", min_length=1)
    status: RunStatus
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    resident_context: ResidentContextReference = Field(alias="residentContext")
    source_text_hash: StrictStr = Field(alias="sourceTextHash", pattern=r"^[a-f0-9]{64}$")
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    source_fact_extraction_run_id: StrictStr = Field(alias="sourceFactExtractionRunId", min_length=1)
    claim_set_id: StrictStr = Field(alias="claimSetId", min_length=1)
    ruleset_version: Literal[RULESET_VERSION] = Field(alias="rulesetVersion")
    coverage_status_policy_version: Literal[STATUS_POLICY_VERSION] = Field(alias="coverageStatusPolicyVersion")
    expectation_policy_version: Literal[EXPECTATION_POLICY_VERSION] = Field(alias="expectationPolicyVersion")
    dataset_version: StrictStr = Field(alias="datasetVersion", min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
    correlation_id: StrictStr = Field(alias="correlationId", min_length=1)
    input_digest: StrictStr = Field(alias="inputDigest", pattern=r"^[a-f0-9]{64}$")
    provider_version: StrictStr | None = Field(default=None, alias="providerVersion", min_length=1)
    model_version: StrictStr | None = Field(default=None, alias="modelVersion", min_length=1)
    prompt_version: StrictStr | None = Field(default=None, alias="promptVersion", min_length=1)
    execution_metrics: ExecutionMetrics = Field(alias="executionMetrics")
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime = Field(alias="completedAt")


class CoverageRunSucceeded(_RunBase):
    status: Literal[RunStatus.SUCCEEDED]
    assessments: tuple[CoverageAssessment, ...]
    findings: tuple[CoverageFinding, ...]
    runtime_counts: CoverageCounts = Field(alias="runtimeCounts")


class CoverageRunFailed(_RunBase):
    status: Literal[RunStatus.FAILED]
    failure: Failure


CoverageRun = CoverageRunSucceeded | CoverageRunFailed


class ApiError(_Contract):
    code: Literal[
        "SOURCE_NOT_FOUND", "SOURCE_VERSION_NOT_FOUND", "NOTE_NOT_FOUND", "SOURCE_FACT_EXTRACTION_NOT_FOUND",
        "CLAIM_SET_NOT_FOUND", "PROVENANCE_CONFLICT", "IDEMPOTENCY_KEY_CONFLICT", "DEPENDENCY_UNAVAILABLE",
        "INTERNAL_ERROR",
    ]
    message: StrictStr = Field(min_length=1)
    correlation_id: StrictStr | None = Field(default=None, alias="correlationId")


class SchemaError(_Contract):
    code: Literal["SCHEMA_ERROR"]
    message: StrictStr = Field(min_length=1)
    path: StrictStr | None = None
