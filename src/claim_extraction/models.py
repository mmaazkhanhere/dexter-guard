"""Strict Pydantic contracts for candidate-note claim extraction."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator


class _Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=False,
    )


class EvidenceSourceReference(_Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    source_text_hash: StrictStr = Field(alias="sourceTextHash", min_length=1)
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)


class TextSpan(_Contract):
    """Zero-based code-point and UTF-16 end-exclusive note coordinates."""

    start_code_point: StrictInt = Field(alias="startCodePoint", ge=0)
    end_code_point_exclusive: StrictInt = Field(alias="endCodePointExclusive", ge=1)
    start_utf16: StrictInt = Field(alias="startUtf16", ge=0)
    end_utf16_exclusive: StrictInt = Field(alias="endUtf16Exclusive", ge=1)
    text: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def require_non_empty_ranges(self) -> "TextSpan":
        if self.end_code_point_exclusive <= self.start_code_point:
            raise ValueError("endCodePointExclusive must be greater than startCodePoint")
        if self.end_utf16_exclusive <= self.start_utf16:
            raise ValueError("endUtf16Exclusive must be greater than startUtf16")
        return self


class NumericRange(_Contract):
    lower: Decimal
    upper: Decimal

    @model_validator(mode="after")
    def lower_must_not_exceed_upper(self) -> "NumericRange":
        if self.lower > self.upper:
            raise ValueError("range.lower must not exceed range.upper")
        return self


class NumericValue(_Contract):
    raw: StrictStr = Field(min_length=1)
    normalized_decimal: Decimal | None = Field(default=None, alias="normalizedDecimal")
    unit_raw: StrictStr | None = Field(default=None, alias="unitRaw", min_length=1)
    unit_normalized: StrictStr | None = Field(default=None, alias="unitNormalized", min_length=1)
    approximation: StrictBool
    range: NumericRange | None = None
    value_span: TextSpan = Field(alias="valueSpan")
    unit_span: TextSpan | None = Field(default=None, alias="unitSpan")

    @model_validator(mode="after")
    def require_unit_pair(self) -> "NumericValue":
        if (self.unit_raw is None) != (self.unit_span is None):
            raise ValueError("unitRaw and unitSpan must be supplied together")
        if self.unit_normalized is not None and self.unit_raw is None:
            raise ValueError("unitNormalized requires unitRaw")
        return self


class MedicationDetails(_Contract):
    name: StrictStr | None = Field(default=None, min_length=1)
    dose_raw: StrictStr | None = Field(default=None, alias="doseRaw", min_length=1)
    route_raw: StrictStr | None = Field(default=None, alias="routeRaw", min_length=1)
    administration_temporal_text: StrictStr | None = Field(
        default=None, alias="administrationTemporalText", min_length=1
    )


class ClaimCategory(StrEnum):
    OBSERVATION = "OBSERVATION"
    SYMPTOM = "SYMPTOM"
    MEASUREMENT = "MEASUREMENT"
    VITAL_SIGN = "VITAL_SIGN"
    MEDICATION = "MEDICATION"
    CARE_ACTION = "CARE_ACTION"
    FUNCTION = "FUNCTION"
    ELIMINATION = "ELIMINATION"
    NUTRITION_HYDRATION = "NUTRITION_HYDRATION"
    SLEEP = "SLEEP"
    BEHAVIOUR = "BEHAVIOUR"
    EVENT = "EVENT"
    CLINICAL_CONCLUSION = "CLINICAL_CONCLUSION"
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


class Claim(_Contract):
    id: StrictStr = Field(min_length=1)
    note_revision_id: StrictStr = Field(alias="noteRevisionId", min_length=1)
    resident_test_id: StrictStr = Field(alias="residentTestId", min_length=1)
    ordinal: StrictInt = Field(ge=1)
    category: ClaimCategory
    statement_span: TextSpan = Field(alias="statementSpan")
    claim_text: StrictStr = Field(alias="claimText", min_length=1)
    subject: StrictStr | None = Field(default=None, min_length=1)
    predicate: StrictStr | None = Field(default=None, min_length=1)
    object: StrictStr | None = Field(default=None, min_length=1)
    polarity: Polarity
    negation_cue: TextSpan | None = Field(default=None, alias="negationCue")
    certainty: Certainty
    certainty_cue: TextSpan | None = Field(default=None, alias="certaintyCue")
    attribution: Attribution
    attribution_text: StrictStr | None = Field(default=None, alias="attributionText", min_length=1)
    attribution_span: TextSpan | None = Field(default=None, alias="attributionSpan")
    temporal_text: StrictStr | None = Field(default=None, alias="temporalText", min_length=1)
    temporal_span: TextSpan | None = Field(default=None, alias="temporalSpan")
    numeric_values: tuple[NumericValue, ...] = Field(alias="numericValues")
    medication: MedicationDetails | None = None
    extraction_warnings: tuple[StrictStr, ...] = Field(alias="extractionWarnings")

    @model_validator(mode="after")
    def enforce_local_contract(self) -> "Claim":
        if self.claim_text != self.statement_span.text:
            raise ValueError("claimText must equal statementSpan.text")
        if self.polarity is Polarity.NEGATED and self.negation_cue is None:
            raise ValueError("NEGATED claims require negationCue")
        if self.certainty in {Certainty.UNCERTAIN, Certainty.POSSIBLE} and self.certainty_cue is None:
            raise ValueError("non-certain claims require certaintyCue")
        if self.attribution is not Attribution.UNSPECIFIED:
            if self.attribution_text is None or self.attribution_span is None:
                raise ValueError("explicit attribution requires attributionText and attributionSpan")
        if (self.attribution_text is None) != (self.attribution_span is None):
            raise ValueError("attributionText and attributionSpan must be supplied together")
        if (self.temporal_text is None) != (self.temporal_span is None):
            raise ValueError("temporalText and temporalSpan must be supplied together")
        if self.attribution_text is not None and self.attribution_text != self.attribution_span.text:
            raise ValueError("attributionText must equal attributionSpan.text")
        if self.temporal_text is not None and self.temporal_text != self.temporal_span.text:
            raise ValueError("temporalText must equal temporalSpan.text")
        return self


class ExtractionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    EMPTY = "EMPTY"
    FAILED = "FAILED"


class ExtractionErrorCode(StrEnum):
    MALFORMED_PROVIDER_OUTPUT = "MALFORMED_PROVIDER_OUTPUT"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    INVALID_SPAN = "INVALID_SPAN"
    REVISION_NOT_FOUND = "REVISION_NOT_FOUND"
    REVISION_MISMATCH = "REVISION_MISMATCH"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    NON_SYNTHETIC_INPUT = "NON_SYNTHETIC_INPUT"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INTERNAL_VALIDATION_ERROR = "INTERNAL_VALIDATION_ERROR"


class ExtractionError(_Contract):
    code: ExtractionErrorCode
    message: StrictStr = Field(min_length=1)
    retryable: StrictBool


class _ResultBase(_Contract):
    extraction_run_id: StrictStr = Field(alias="extractionRunId", min_length=1)
    extractor_version: StrictStr = Field(alias="extractorVersion", min_length=1)
    provider_version: StrictStr | None = Field(default=None, alias="providerVersion", min_length=1)
    model_version: StrictStr | None = Field(default=None, alias="modelVersion", min_length=1)
    prompt_version: StrictStr | None = Field(default=None, alias="promptVersion", min_length=1)
    output_schema_version: StrictStr = Field(alias="outputSchemaVersion", min_length=1)
    claims: tuple[Claim, ...]
    extracted_at: datetime = Field(alias="extractedAt")

    @field_validator("extracted_at")
    @classmethod
    def extracted_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("extractedAt must be timezone-aware")
        return value


class _SuccessfulBase(_ResultBase):
    note_revision_id: StrictStr = Field(alias="noteRevisionId", min_length=1)
    note_body_hash: StrictStr = Field(alias="noteBodyHash", min_length=1)
    evidence_source_reference: EvidenceSourceReference = Field(alias="evidenceSourceReference")


class ExtractionSucceeded(_SuccessfulBase):
    status: Literal[ExtractionStatus.SUCCEEDED] = ExtractionStatus.SUCCEEDED
    claims: tuple[Claim, ...] = Field(min_length=1)


class ExtractionEmpty(_SuccessfulBase):
    status: Literal[ExtractionStatus.EMPTY] = ExtractionStatus.EMPTY
    claims: tuple[Claim, ...] = Field(default_factory=tuple, max_length=0)


class ExtractionFailed(_ResultBase):
    status: Literal[ExtractionStatus.FAILED] = ExtractionStatus.FAILED
    note_revision_id: StrictStr | None = Field(default=None, alias="noteRevisionId", min_length=1)
    note_body_hash: StrictStr | None = Field(default=None, alias="noteBodyHash", min_length=1)
    claims: tuple[Claim, ...] = Field(default_factory=tuple, max_length=0)
    error: ExtractionError


ExtractionResult: TypeAlias = Annotated[
    ExtractionSucceeded | ExtractionEmpty | ExtractionFailed,
    Field(discriminator="status"),
]
