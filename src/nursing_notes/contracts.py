"""Strict Pydantic contracts for candidate nursing notes and facts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator


class _Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=False,
    )


class ExternalOrigin(_Contract):
    system: StrictStr = Field(min_length=1)
    external_note_id: StrictStr = Field(alias="externalNoteId", min_length=1)


class SourceReference(_Contract):
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)


class GenerateRequest(SourceReference):
    requested_by: StrictStr = Field(alias="requestedBy", min_length=1)


class ImportRequest(SourceReference):
    content: StrictStr = Field(min_length=1)
    external_origin: ExternalOrigin = Field(alias="externalOrigin")
    requested_by: StrictStr = Field(alias="requestedBy", min_length=1)
    facts: tuple["CandidateNursingFact", ...] = Field(default_factory=tuple)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class SourceAnchor(_Contract):
    """A source span or an explicit external provenance anchor."""

    source_id: StrictStr | None = Field(default=None, alias="sourceId", min_length=1)
    source_version: StrictInt | None = Field(default=None, alias="sourceVersion", ge=1)
    start: StrictInt | None = Field(default=None, ge=0)
    end: StrictInt | None = Field(default=None, ge=1)
    external_system: StrictStr | None = Field(default=None, alias="externalSystem", min_length=1)
    external_fact_id: StrictStr | None = Field(default=None, alias="externalFactId", min_length=1)

    @model_validator(mode="after")
    def require_source_or_external_reference(self) -> "SourceAnchor":
        source_fields = (self.source_id, self.source_version, self.start, self.end)
        has_source = all(value is not None for value in source_fields)
        has_external = self.external_system is not None and self.external_fact_id is not None
        if not has_source and not has_external:
            raise ValueError("sourceAnchor must identify a source span or external provenance")
        if (self.external_system is None) != (self.external_fact_id is None):
            raise ValueError("external provenance requires both externalSystem and externalFactId")
        if any(value is not None for value in source_fields) and not has_source:
            raise ValueError("sourceAnchor source fields must be supplied together")
        if self.start is not None and self.end is not None and self.start >= self.end:
            raise ValueError("sourceAnchor must use a non-empty half-open span")
        return self


FactType = Literal["OBSERVATION", "SYMPTOM", "MEASUREMENT", "ACTION"]
Polarity = Literal["AFFIRMED", "NEGATED"]
Certainty = Literal["CERTAIN", "UNCERTAIN"]
Provenance = Literal["GENERATED_FROM_SOURCE", "EXTERNALLY_SUPPLIED"]


class CandidateNursingFact(_Contract):
    """A provider or external-candidate fact before repository identity fields."""

    type: FactType
    statement: StrictStr = Field(min_length=1)
    resident_subject: StrictStr = Field(alias="residentSubject", min_length=1)
    source_anchor: SourceAnchor = Field(alias="sourceAnchor")
    polarity: Polarity | None = None
    certainty: Certainty | None = None
    attribution: StrictStr | None = Field(default=None, min_length=1)
    temporal_qualifier: StrictStr | None = Field(default=None, alias="temporalQualifier", min_length=1)
    numeric_value: StrictStr | None = Field(default=None, alias="numericValue", min_length=1)
    unit: StrictStr | None = Field(default=None, min_length=1)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_value_unit_pair(self) -> "CandidateNursingFact":
        if (self.numeric_value is None) != (self.unit is None):
            raise ValueError("numericValue and unit must be supplied together")
        return self


class NursingFact(CandidateNursingFact):
    """A persisted candidate fact tied to one note revision."""

    fact_id: StrictStr = Field(alias="factId", min_length=1)
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    revision: StrictInt = Field(ge=1)


class GenerationResult(_Contract):
    content: StrictStr = Field(min_length=1)
    facts: tuple[CandidateNursingFact, ...]
    generation_run_id: StrictStr | None = Field(default=None, alias="generationRunId", min_length=1)
    model_id: StrictStr | None = Field(default=None, alias="modelId", min_length=1)
    prompt_version: StrictStr | None = Field(default=None, alias="promptVersion", min_length=1)
    schema_version: StrictStr | None = Field(default=None, alias="schemaVersion", min_length=1)
    ruleset_version: StrictStr | None = Field(default=None, alias="rulesetVersion", min_length=1)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class NoteResponse(_Contract):
    note_id: StrictStr = Field(alias="noteId", min_length=1)
    revision: StrictInt = Field(ge=1)
    previous_revision_id: StrictStr | None = Field(default=None, alias="previousRevisionId")
    content: StrictStr = Field(min_length=1)
    status: Literal["DRAFT"]
    origin: Literal["GENERATED", "IMPORTED"]
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    validation_run_id: StrictStr = Field(alias="validationRunId", min_length=1)
    external_origin: ExternalOrigin | None = Field(default=None, alias="externalOrigin")
    facts: tuple[NursingFact, ...]
    generation_run_id: StrictStr | None = Field(default=None, alias="generationRunId")
    model_id: StrictStr | None = Field(default=None, alias="modelId")
    prompt_version: StrictStr | None = Field(default=None, alias="promptVersion")
    schema_version: StrictStr = Field(alias="schemaVersion", min_length=1)
    ruleset_version: StrictStr = Field(alias="rulesetVersion", min_length=1)
    source_text_hash: StrictStr = Field(alias="sourceTextHash", min_length=1)
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)
    created_at: datetime = Field(alias="createdAt")
    created_by: StrictStr = Field(alias="createdBy", min_length=1)


class NoteRevisionRecord(_Contract):
    """Internal persisted revision; all fields are also exposed in the response."""

    note_id: StrictStr = Field(alias="noteId", min_length=1)
    revision: StrictInt = Field(ge=1)
    previous_revision_id: StrictStr | None = Field(default=None, alias="previousRevisionId")
    content: StrictStr = Field(min_length=1)
    status: Literal["DRAFT"]
    origin: Literal["GENERATED", "IMPORTED"]
    source_id: StrictStr = Field(alias="sourceId", min_length=1)
    source_version: StrictInt = Field(alias="sourceVersion", ge=1)
    external_origin: ExternalOrigin | None = Field(default=None, alias="externalOrigin")
    validation_run_id: StrictStr = Field(alias="validationRunId", min_length=1)
    facts: tuple[NursingFact, ...]
    generation_run_id: StrictStr | None = Field(default=None, alias="generationRunId")
    model_id: StrictStr | None = Field(default=None, alias="modelId")
    prompt_version: StrictStr | None = Field(default=None, alias="promptVersion")
    schema_version: StrictStr = Field(alias="schemaVersion", min_length=1)
    ruleset_version: StrictStr = Field(alias="rulesetVersion", min_length=1)
    source_text_hash: StrictStr = Field(alias="sourceTextHash", min_length=1)
    normalization_policy: StrictStr = Field(alias="normalizationPolicy", min_length=1)
    created_at: datetime = Field(alias="createdAt")
    created_by: StrictStr = Field(alias="createdBy", min_length=1)

    def response(self) -> NoteResponse:
        return NoteResponse.model_validate(self.model_dump())


CandidateNursingFact.model_rebuild()
