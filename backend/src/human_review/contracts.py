from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

CONTRACT_VERSION = "REVIEW-AUDIT-CONTRACT-v1"
SEVERITY_POLICY_VERSION = "REVIEW_SEVERITY-v2"
LEGACY_SEVERITY_POLICY_VERSION = "REVIEW_SEVERITY-v1"
APPROVAL_POLICY_VERSION = "REVIEW_APPROVAL-v1"


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, str_strip_whitespace=False)


class SourceReference(Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)


class NoteSpan(Contract):
    start_code_point: StrictInt = Field(alias="startCodePoint", ge=0)
    end_code_point_exclusive: StrictInt = Field(alias="endCodePointExclusive", ge=1)
    text: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def non_empty(self) -> "NoteSpan":
        if self.end_code_point_exclusive <= self.start_code_point:
            raise ValueError("note span must be non-empty")
        return self


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


class EvidenceDisplay(Contract):
    availability: Literal["AVAILABLE", "MISSING", "INVALID"]
    spans: tuple[SourceSpan, ...] = ()
    excerpts: tuple[StrictStr, ...] = ()

    @model_validator(mode="after")
    def closure(self) -> "EvidenceDisplay":
        if self.availability == "AVAILABLE" and (not self.spans or len(self.spans) != len(self.excerpts)):
            raise ValueError("available evidence requires paired spans and excerpts")
        if self.availability != "AVAILABLE" and (self.spans or self.excerpts):
            raise ValueError("unavailable evidence cannot expose spans")
        return self


class ReviewFinding(Contract):
    review_finding_id: StrictStr = Field(alias="reviewFindingId", min_length=1)
    origin: Literal["SPEC_004", "SPEC_005", "SPEC_006", "REVIEW_OPERATIONAL"]
    origin_run_id: StrictStr | None = Field(default=None, alias="originRunId")
    origin_finding_id: StrictStr | None = Field(default=None, alias="originFindingId")
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    claim_id: StrictStr | None = Field(default=None, alias="claimId")
    claim_span: NoteSpan | None = Field(default=None, alias="claimSpan")
    upstream_status: StrictStr | None = Field(default=None, alias="upstreamStatus")
    rule_code: StrictStr | None = Field(default=None, alias="ruleCode")
    severity: Literal["CRITICAL", "MAJOR", "MINOR"]
    severity_policy_version: Literal[LEGACY_SEVERITY_POLICY_VERSION, SEVERITY_POLICY_VERSION] = Field(alias="severityPolicyVersion")
    severity_rationale: StrictStr = Field(alias="severityRationale", min_length=1)
    explanation: StrictStr = Field(min_length=1)
    evidence: EvidenceDisplay
    state: Literal["OPEN", "RESOLVED", "ADJUDICATED", "STALE"]
    created_at: datetime = Field(alias="createdAt")

    @model_validator(mode="after")
    def upstream_identity(self) -> "ReviewFinding":
        if self.origin == "REVIEW_OPERATIONAL":
            return self
        if not self.origin_run_id or not self.origin_finding_id:
            raise ValueError("upstream findings require origin run and finding identities")
        return self


class SuggestedCorrection(Contract):
    suggestion_id: StrictStr = Field(alias="suggestionId", min_length=1)
    finding_id: StrictStr = Field(alias="findingId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    base_revision: StrictInt = Field(alias="baseRevision", ge=1)
    replacement: StrictStr = Field(min_length=1)
    target_note_span: NoteSpan = Field(alias="targetNoteSpan")
    support_status: Literal["USABLE", "UNUSABLE", "REJECTED"] = Field(alias="supportStatus")
    support_spans: tuple[SourceSpan, ...] = Field(alias="supportSpans")
    generated_by: Literal["REVIEWER", "SPEC_007_CORRECTION_ADAPTER"] = Field(alias="generatedBy")
    created_at: datetime = Field(alias="createdAt")

    @model_validator(mode="after")
    def usable_support(self) -> "SuggestedCorrection":
        if self.support_status == "USABLE" and not self.support_spans:
            raise ValueError("usable suggestions require source support")
        return self


class ReviewDecision(Contract):
    review_decision_id: StrictStr = Field(alias="reviewDecisionId", min_length=1)
    finding_id: StrictStr = Field(alias="findingId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    kind: Literal["ACKNOWLEDGED", "DISPUTED", "ADJUDICATED", "MANUAL_CORRECTION_RECORDED", "SUGGESTION_ACCEPTED", "SUGGESTION_REJECTED"]
    outcome: Literal["NO_STATE_CHANGE", "OPEN", "ADJUDICATED", "RESOLVED", "STALE"]
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    rationale: StrictStr | None = None
    successor_revision: StrictInt | None = Field(default=None, alias="successorRevision")
    suggestion_id: StrictStr | None = Field(default=None, alias="suggestionId")
    idempotency_key: StrictStr | None = Field(default=None, alias="idempotencyKey")
    recorded_at: datetime = Field(alias="recordedAt")

    @model_validator(mode="after")
    def rationale_rules(self) -> "ReviewDecision":
        if self.kind in {"DISPUTED", "ADJUDICATED", "SUGGESTION_REJECTED"} and not self.rationale:
            raise ValueError("this decision kind requires rationale")
        if self.kind == "SUGGESTION_ACCEPTED" and (not self.suggestion_id or self.successor_revision is None):
            raise ValueError("accepted suggestion requires suggestion and successor revision")
        return self


class ComponentStatus(Contract):
    component: Literal["CLAIM_EXTRACTION", "EVIDENCE_VERIFICATION", "DETERMINISTIC_VALIDATION", "SOURCE_COVERAGE"]
    run_id: StrictStr | None = Field(alias="runId")
    status: Literal["SUCCEEDED", "FAILED", "INVALID", "UNAVAILABLE"]
    failure_code: StrictStr | None = Field(default=None, alias="failureCode")


class FullNoteVerification(Contract):
    full_verification_id: StrictStr = Field(alias="fullVerificationId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    source: SourceReference
    claim_set_id: StrictStr = Field(alias="claimSetId", min_length=1)
    evidence_run_id: StrictStr = Field(alias="evidenceRunId", min_length=1)
    deterministic_validation_run_id: StrictStr = Field(alias="deterministicValidationRunId", min_length=1)
    coverage_run_id: StrictStr = Field(alias="coverageRunId", min_length=1)
    coverage_unresolved_source_items: StrictInt = Field(default=0, alias="coverageUnresolvedSourceItems", ge=0)
    component_statuses: tuple[ComponentStatus, ...] = Field(alias="componentStatuses", min_length=4, max_length=4)
    status: Literal["VALID", "INVALID", "FAILED"]
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
    request_digest: StrictStr = Field(alias="requestDigest", min_length=1)
    correlation_id: StrictStr | None = Field(default=None, alias="correlationId")
    failure_code: StrictStr | None = Field(default=None, alias="failureCode")
    failure_message: StrictStr | None = Field(default=None, alias="failureMessage")
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")

    @model_validator(mode="after")
    def terminal_closure(self) -> "FullNoteVerification":
        if self.completed_at is None:
            object.__setattr__(self, "completed_at", self.created_at)
        components = [item.component for item in self.component_statuses]
        if set(components) != {"CLAIM_EXTRACTION", "EVIDENCE_VERIFICATION", "DETERMINISTIC_VALIDATION", "SOURCE_COVERAGE"}:
            raise ValueError("full verification must contain exactly one status per component")
        if self.status == "VALID" and any(item.status != "SUCCEEDED" for item in self.component_statuses):
            raise ValueError("valid verification requires all components to succeed")
        if self.status != "VALID" and (not self.failure_code or not self.failure_message):
            raise ValueError("failed or invalid verification requires a safe failure")
        if self.status == "VALID" and self.coverage_unresolved_source_items:
            raise ValueError("unresolved source items block valid approval")
        if self.status == "VALID" and any(item.run_id is None for item in self.component_statuses):
            raise ValueError("valid verification requires a run id for every component")
        return self


class NoteDisposition(Contract):
    disposition_id: StrictStr = Field(alias="dispositionId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    kind: Literal["APPROVED", "REJECTED"]
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    reason: StrictStr | None = None
    full_verification_id: StrictStr | None = Field(default=None, alias="fullVerificationId")
    eligibility_policy_version: StrictStr | None = Field(default=None, alias="eligibilityPolicyVersion")
    decided_at: datetime = Field(alias="decidedAt")

    @model_validator(mode="after")
    def rejection_reason(self) -> "NoteDisposition":
        if self.kind == "REJECTED" and not self.reason:
            raise ValueError("rejection requires a reason")
        return self


class AuditEvent(Contract):
    event_id: StrictStr = Field(alias="eventId", min_length=1)
    sequence: StrictInt = Field(ge=1)
    occurred_at: datetime = Field(alias="occurredAt")
    actor_label: StrictStr = Field(alias="actorLabel", min_length=1)
    event_type: StrictStr = Field(alias="eventType", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    target_type: StrictStr = Field(alias="targetType", min_length=1)
    target_id: StrictStr = Field(alias="targetId", min_length=1)
    references: tuple[StrictStr, ...] = ()
    payload_digest: StrictStr = Field(alias="payloadDigest", min_length=1)
    rationale: StrictStr | None = None


class ClaimReverificationResponse(Contract):
    review_verification_id: StrictStr = Field(alias="reviewVerificationId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    source: SourceReference
    upstream_verification_run_id: StrictStr = Field(alias="upstreamVerificationRunId", min_length=1)
    status: Literal["SUCCEEDED", "FAILED", "INVALID"]
    approval_eligible: Literal[False] = Field(alias="approvalEligible")


class SaveRevisionRequest(Contract):
    expected_revision: StrictInt = Field(alias="expectedRevision", ge=1)
    content: StrictStr = Field(min_length=1)
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    finding_id: StrictStr | None = Field(default=None, alias="findingId")
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)


class FindingDecisionRequest(Contract):
    expected_revision: StrictInt = Field(alias="expectedRevision", ge=1)
    kind: Literal["ACKNOWLEDGED", "DISPUTED", "ADJUDICATED", "SUGGESTION_ACCEPTED", "SUGGESTION_REJECTED"]
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    rationale: StrictStr | None = Field(default=None, min_length=1)
    suggestion_id: StrictStr | None = Field(default=None, alias="suggestionId")
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)

    @model_validator(mode="after")
    def conditional_fields(self) -> "FindingDecisionRequest":
        if self.kind in {"SUGGESTION_ACCEPTED", "SUGGESTION_REJECTED"} and not self.suggestion_id:
            raise ValueError("suggestionId is required for suggestion decisions")
        if self.kind in {"DISPUTED", "ADJUDICATED", "SUGGESTION_REJECTED"} and not self.rationale:
            raise ValueError("rationale is required for this decision")
        return self


class ClaimReverificationRequest(Contract):
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)


class FullVerificationRequest(Contract):
    expected_revision: StrictInt = Field(alias="expectedRevision", ge=1)
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)


class ApproveRequest(Contract):
    expected_revision: StrictInt = Field(alias="expectedRevision", ge=1)
    full_verification_id: StrictStr = Field(alias="fullVerificationId", min_length=1)
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    rationale: StrictStr | None = Field(default=None, min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)


class RejectRequest(Contract):
    expected_revision: StrictInt = Field(alias="expectedRevision", ge=1)
    reviewer_label: StrictStr = Field(alias="reviewerLabel", min_length=1)
    reason: StrictStr = Field(min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
