"""Pydantic contracts for immutable source documents and evidence spans."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator


_RESIDENT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"


class _StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=False)


class SourceDocument(_StrictContract):
    """One immutable, exact version of one synthetic-resident transcript."""

    source_id: StrictStr = Field(min_length=1)
    source_version: StrictInt = Field(ge=1)
    resident_test_id: StrictStr = Field(min_length=1, pattern=_RESIDENT_ID_PATTERN)
    language: Literal["de-DE"]
    transcript_text: StrictStr = Field(min_length=1)
    created_at: datetime

    @field_validator("transcript_text")
    @classmethod
    def transcript_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript_text must not be blank")
        return value

    @field_validator("created_at")
    @classmethod
    def creation_time_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class SourceSpan(_StrictContract):
    """A source/version-bound half-open Unicode scalar-value range."""

    source_id: StrictStr = Field(min_length=1)
    source_version: StrictInt = Field(ge=1)
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(ge=1)


class ResolvedSourceSpan(SourceSpan):
    """A validated span plus its non-authoritative derived excerpt."""

    text: StrictStr


class CreateSourceRequest(_StrictContract):
    """Request for a new source identity at version one."""

    resident_test_id: StrictStr = Field(min_length=1, pattern=_RESIDENT_ID_PATTERN)
    language: Literal["de-DE"]
    transcript_text: StrictStr = Field(min_length=1)

    @field_validator("transcript_text")
    @classmethod
    def transcript_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript_text must not be blank")
        return value


class CreateSourceVersionRequest(_StrictContract):
    """Request for an optimistic-concurrency checked immutable revision."""

    expected_source_version: StrictInt = Field(ge=1)
    transcript_text: StrictStr = Field(min_length=1)

    @field_validator("transcript_text")
    @classmethod
    def transcript_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transcript_text must not be blank")
        return value
