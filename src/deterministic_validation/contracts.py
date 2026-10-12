"""Versioned Pydantic contracts for the deterministic validation boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator


CONTRACT_VERSION = "DVE-CONTRACT-v1"
RULESET_VERSION = "DVE-RULESET-v1"
ENGINE_VERSION = "DVE-ENGINE-v1"


class _Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=False,
    )


class Approximation(StrEnum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    UNSPECIFIED = "UNSPECIFIED"


class MeasurementCategory(StrEnum):
    TEMPERATURE = "TEMPERATURE"
    FLUID_INTAKE = "FLUID_INTAKE"
    MEDICATION_QUANTITY = "MEDICATION_QUANTITY"
    BLOOD_PRESSURE = "BLOOD_PRESSURE"


class Unit(StrEnum):
    CELSIUS = "CELSIUS"
    MILLILITRE = "MILLILITRE"
    LITRE = "LITRE"
    MILLIGRAM = "MILLIGRAM"
    GRAM = "GRAM"
    MMHG = "MMHG"


class AlignmentStatus(StrEnum):
    ALIGNED = "ALIGNED"
    UNAVAILABLE = "UNAVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"
    REJECTED = "REJECTED"


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ReasonCode(StrEnum):
    ALIGNMENT_UNAVAILABLE = "ALIGNMENT_UNAVAILABLE"
    ALIGNMENT_AMBIGUOUS = "ALIGNMENT_AMBIGUOUS"
    ALIGNMENT_REJECTED = "ALIGNMENT_REJECTED"
    NUMERIC_MISMATCH = "NUMERIC_MISMATCH"
    INCOMPATIBLE_UNIT = "INCOMPATIBLE_UNIT"
    PRECISION_MISMATCH = "PRECISION_MISMATCH"
    COMPOSITE_MEASUREMENT_MISMATCH = "COMPOSITE_MEASUREMENT_MISMATCH"
    INVALID_STRUCTURED_FIELD_TYPE = "INVALID_STRUCTURED_FIELD_TYPE"
    MISSING_REQUIRED_REFERENCE = "MISSING_REQUIRED_REFERENCE"
    INVALID_UNIT_CATEGORY_PAIRING = "INVALID_UNIT_CATEGORY_PAIRING"
    INVALID_SOURCE_SPAN = "INVALID_SOURCE_SPAN"
    SOURCE_VERSION_MISMATCH = "SOURCE_VERSION_MISMATCH"
    EVIDENCE_TEXT_MISMATCH = "EVIDENCE_TEXT_MISMATCH"


class TranscriptSnapshot(_Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    transcript_text: StrictStr = Field(alias="transcriptText", min_length=1)


class EvidenceReference(_Contract):
    """A source-bound reference; boundary validity is a deterministic rule result."""

    evidence_reference_id: StrictStr = Field(alias="evidenceReferenceId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion")
    start: StrictInt
    end: StrictInt
    quoted_text: StrictStr = Field(alias="quotedText")


class ScalarMeasurement(_Contract):
    category: Literal[
        MeasurementCategory.TEMPERATURE,
        MeasurementCategory.FLUID_INTAKE,
        MeasurementCategory.MEDICATION_QUANTITY,
    ]
    value: StrictStr
    unit: Unit
    approximation: Approximation


class BloodPressureValue(_Contract):
    systolic: StrictInt | StrictStr
    diastolic: StrictInt | StrictStr


class BloodPressureMeasurement(_Contract):
    category: Literal[MeasurementCategory.BLOOD_PRESSURE]
    value: BloodPressureValue
    unit: Unit
    approximation: Approximation


Measurement: TypeAlias = Annotated[
    ScalarMeasurement | BloodPressureMeasurement,
    Field(discriminator="category"),
]


class SourceFact(_Contract):
    source_fact_id: StrictStr = Field(alias="sourceFactId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion")
    measurement: Measurement
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1)


class Claim(_Contract):
    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt | None = Field(alias="noteRevision")
    measurement: Measurement
    evidence: tuple[EvidenceReference, ...] = ()


class Alignment(_Contract):
    alignment_id: StrictStr = Field(alias="alignmentId", min_length=1)
    source_fact_id: StrictStr = Field(alias="sourceFactId", min_length=1)
    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    status: AlignmentStatus


class ValidationRequest(_Contract):
    ruleset_version: Literal[RULESET_VERSION] = Field(alias="rulesetVersion")
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    source_fact_ids: tuple[StrictStr, ...] = Field(alias="sourceFactIds", min_length=1)
    claim_ids: tuple[StrictStr, ...] = Field(alias="claimIds", min_length=1)
    alignment_ids: tuple[StrictStr, ...] = Field(alias="alignmentIds", min_length=1)

    @model_validator(mode="after")
    def require_distinct_ids(self) -> "ValidationRequest":
        for field_name in ("source_fact_ids", "claim_ids", "alignment_ids"):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must contain unique IDs")
        return self


class ValidationFinding(_Contract):
    rule_id: StrictStr = Field(alias="ruleId", pattern=r"^(ALIGN|NUM|STR|EVD)-[0-9]{3}$")
    rule_version: Literal["1"] = Field(alias="ruleVersion")
    ruleset_version: Literal[RULESET_VERSION] = Field(alias="rulesetVersion")
    outcome: Literal[Outcome.FAIL, Outcome.NOT_EVALUABLE]
    source_fact_id: StrictStr | None = Field(alias="sourceFactId")
    claim_id: StrictStr | None = Field(alias="claimId")
    alignment_id: StrictStr | None = Field(alias="alignmentId")
    evidence_reference_ids: tuple[StrictStr, ...] = Field(alias="evidenceReferenceIds")
    expected_value: object | None = Field(alias="expectedValue")
    observed_value: object | None = Field(alias="observedValue")
    unit: StrictStr | None
    requires_review: Literal[True] = Field(alias="requiresReview")
    reason_code: ReasonCode = Field(alias="reasonCode")
    message: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def validate_conditional_traceability(self) -> "ValidationFinding":
        family = self.rule_id.split("-", 1)[0]
        if family in {"ALIGN", "NUM", "STR"}:
            if not self.source_fact_id or not self.claim_id or not self.alignment_id:
                raise ValueError("ALIGN, NUM, and STR findings require pair identifiers")
        if family == "EVD":
            if not self.evidence_reference_ids or not (self.source_fact_id or self.claim_id):
                raise ValueError("EVD findings require evidence and an owning record")
        if self.rule_id in {"NUM-001", "NUM-003", "NUM-004", "NUM-005"}:
            if self.expected_value is None or self.observed_value is None or not self.unit:
                raise ValueError(f"{self.rule_id} requires expected, observed, and unit")
        return self


class ValidationRun(_Contract):
    validation_run_id: StrictStr = Field(alias="validationRunId", min_length=1)
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    note_revision: StrictInt = Field(alias="noteRevision", ge=1)
    input_digest: StrictStr = Field(alias="inputDigest", pattern=r"^[a-f0-9]{64}$")
    engine_version: StrictStr = Field(alias="engineVersion", min_length=1)
    contract_version: Literal[CONTRACT_VERSION] = Field(alias="contractVersion")
    ruleset_version: Literal[RULESET_VERSION] = Field(alias="rulesetVersion")
    findings: tuple[ValidationFinding, ...]


class ApiErrorCode(StrEnum):
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_VERSION_NOT_FOUND = "SOURCE_VERSION_NOT_FOUND"
    SOURCE_FACT_NOT_FOUND = "SOURCE_FACT_NOT_FOUND"
    CLAIM_NOT_FOUND = "CLAIM_NOT_FOUND"
    ALIGNMENT_NOT_FOUND = "ALIGNMENT_NOT_FOUND"
    PROVENANCE_CONFLICT = "PROVENANCE_CONFLICT"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SchemaError(_Contract):
    code: Literal["SCHEMA_ERROR"]
    message: StrictStr = Field(min_length=1)
    path: StrictStr | None = None


class ApiError(_Contract):
    code: ApiErrorCode
    message: StrictStr = Field(min_length=1)
    correlation_id: StrictStr | None = Field(default=None, alias="correlationId")

