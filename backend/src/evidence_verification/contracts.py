"""Strict Pydantic transport contracts for evidence-verification runs.

Cross-record and source-text invariants intentionally live in ``validation``:
OpenAPI cannot compare sibling arrays or calculate offsets against a source.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator


ANNOTATION_POLICY_VERSION = "EVIDENCE_ANNOTATION-v1"
EVIDENCE_STATUS_POLICY_VERSION = "EVIDENCE_STATUS-v1"


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, str_strip_whitespace=False)


class EvidenceStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNCERTAIN = "UNCERTAIN"


class EvidenceRole(StrEnum):
    SUPPORTING = "SUPPORTING"
    CONFLICTING = "CONFLICTING"
    CONTEXT_NON_SUPPORTING = "CONTEXT_NON_SUPPORTING"


class Discrepancy(StrEnum):
    NEGATION = "NEGATION"
    CERTAINTY = "CERTAINTY"
    ATTRIBUTION = "ATTRIBUTION"
    CLINICAL_INFERENCE = "CLINICAL_INFERENCE"
    OTHER = "OTHER"


class VerificationRunStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    FAILED_EVIDENCE_INTEGRITY = "FAILED_EVIDENCE_INTEGRITY"
    FAILED_VERIFIER = "FAILED_VERIFIER"
    FAILED_PERSISTENCE = "FAILED_PERSISTENCE"


class ClaimInput(_Contract):
    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    resident_test_id: StrictStr = Field(
        alias="residentTestId",
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )

    @field_validator("resident_test_id")
    @classmethod
    def resident_must_be_known(cls, value: str) -> str:
        if value == "UNKNOWN":
            raise ValueError("residentTestId must be a known synthetic resident")
        return value


class VerificationRunRequest(_Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    claim_set_id: StrictStr = Field(alias="claimSetId", min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
    claims: tuple[ClaimInput, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def claim_ids_must_be_distinct(self) -> "VerificationRunRequest":
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claimId values must be distinct")
        return self


class SourceSpan(_Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(ge=1)

    @model_validator(mode="after")
    def end_must_be_end_exclusive(self) -> "SourceSpan":
        if self.end <= self.start:
            raise ValueError("end must be greater than start for an end-exclusive span")
        return self


class EvidenceQuote(_Contract):
    span: SourceSpan
    text: StrictStr = Field(min_length=1)
    evidence_role: EvidenceRole = Field(alias="evidenceRole")


class VerifierFinding(_Contract):
    status: EvidenceStatus
    explanation: StrictStr = Field(min_length=1)


class DeterministicRuleFinding(_Contract):
    code: StrictStr = Field(min_length=1)
    outcome: Literal["PASS", "WARNING", "BLOCKING_FAILURE"]


class EvidenceFinding(_Contract):
    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    status: EvidenceStatus
    explanation: StrictStr = Field(min_length=1)
    source_spans: tuple[SourceSpan, ...] = Field(alias="sourceSpans")
    evidence_quotes: tuple[EvidenceQuote, ...] = Field(alias="evidenceQuotes")
    discrepancies: tuple[Discrepancy, ...]
    policy_version: Literal["EVIDENCE_ANNOTATION-v1"] = Field(alias="policyVersion")
    verifier_finding: VerifierFinding = Field(alias="verifierFinding")
    deterministic_rule_findings: tuple[DeterministicRuleFinding, ...] = Field(alias="deterministicRuleFindings")

    @model_validator(mode="after")
    def enforce_status_evidence_rules(self) -> "EvidenceFinding":
        if self.status is EvidenceStatus.UNSUPPORTED:
            if any(quote.evidence_role is not EvidenceRole.CONTEXT_NON_SUPPORTING for quote in self.evidence_quotes):
                raise ValueError("UNSUPPORTED evidenceQuotes must be CONTEXT_NON_SUPPORTING")
        else:
            if not self.source_spans or not self.evidence_quotes:
                raise ValueError(f"{self.status.value} findings require sourceSpans and evidenceQuotes")
            if any(quote.evidence_role is EvidenceRole.CONTEXT_NON_SUPPORTING for quote in self.evidence_quotes):
                raise ValueError("CONTEXT_NON_SUPPORTING is valid only for UNSUPPORTED findings")
        if len(self.source_spans) != len(self.evidence_quotes):
            raise ValueError("sourceSpans and evidenceQuotes must be paired one-to-one")
        span_keys = [(span.source_id, span.source_version, span.start, span.end) for span in self.source_spans]
        quote_keys = [(quote.span.source_id, quote.span.source_version, quote.span.start, quote.span.end) for quote in self.evidence_quotes]
        if len(set(span_keys)) != len(span_keys):
            raise ValueError("sourceSpans must not contain duplicate spans")
        if set(span_keys) != set(quote_keys) or len(set(quote_keys)) != len(quote_keys):
            raise ValueError("every sourceSpan must have exactly one matching evidenceQuote span")
        return self


class VerificationRunSucceeded(_Contract):
    verification_run_id: StrictStr = Field(alias="verificationRunId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    claim_set_id: StrictStr = Field(alias="claimSetId", min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
    input_digest: StrictStr = Field(alias="inputDigest", min_length=1)
    evidence_status_policy_version: Literal["EVIDENCE_STATUS-v1"] = Field(alias="evidenceStatusPolicyVersion")
    annotation_policy_version: Literal["EVIDENCE_ANNOTATION-v1"] = Field(alias="annotationPolicyVersion")
    model_id: StrictStr = Field(alias="modelId", min_length=1)
    model_version: StrictStr = Field(alias="modelVersion", min_length=1)
    prompt_version: StrictStr = Field(alias="promptVersion", min_length=1)
    prompt_hash: StrictStr = Field(alias="promptHash", min_length=1)
    correlation_id: StrictStr = Field(alias="correlationId", min_length=1)
    execution_trace_id: StrictStr = Field(alias="executionTraceId", min_length=1)
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime = Field(alias="completedAt")
    status: Literal["SUCCEEDED"]
    findings: tuple[EvidenceFinding, ...] = Field(min_length=1)

    @field_validator("created_at", "started_at", "completed_at")
    @classmethod
    def timestamps_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def timestamps_must_be_ordered(self) -> "VerificationRunSucceeded":
        if not self.created_at <= self.started_at <= self.completed_at:
            raise ValueError("createdAt, startedAt, and completedAt must be ordered")
        return self


class VerificationFailure(_Contract):
    code: StrictStr = Field(min_length=1)
    reason: StrictStr = Field(min_length=1)


class VerificationRunFailed(_Contract):
    verification_run_id: StrictStr = Field(alias="verificationRunId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    claim_set_id: StrictStr = Field(alias="claimSetId", min_length=1)
    idempotency_key: StrictStr = Field(alias="idempotencyKey", min_length=1)
    input_digest: StrictStr = Field(alias="inputDigest", min_length=1)
    evidence_status_policy_version: Literal["EVIDENCE_STATUS-v1"] = Field(alias="evidenceStatusPolicyVersion")
    annotation_policy_version: Literal["EVIDENCE_ANNOTATION-v1"] = Field(alias="annotationPolicyVersion")
    model_id: StrictStr | None = Field(default=None, alias="modelId", min_length=1)
    model_version: StrictStr | None = Field(default=None, alias="modelVersion", min_length=1)
    prompt_version: StrictStr | None = Field(default=None, alias="promptVersion", min_length=1)
    prompt_hash: StrictStr | None = Field(default=None, alias="promptHash", min_length=1)
    correlation_id: StrictStr = Field(alias="correlationId", min_length=1)
    execution_trace_id: StrictStr = Field(alias="executionTraceId", min_length=1)
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime = Field(alias="completedAt")
    status: Literal[
        "FAILED_VALIDATION",
        "FAILED_EVIDENCE_INTEGRITY",
        "FAILED_VERIFIER",
        "FAILED_PERSISTENCE",
    ]
    failure: VerificationFailure

    @field_validator("created_at", "started_at", "completed_at")
    @classmethod
    def timestamps_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def timestamps_must_be_ordered(self) -> "VerificationRunFailed":
        if not self.created_at <= self.started_at <= self.completed_at:
            raise ValueError("createdAt, startedAt, and completedAt must be ordered")
        return self


VerificationRun: TypeAlias = Annotated[
    VerificationRunSucceeded | VerificationRunFailed,
    Field(discriminator="status"),
]
