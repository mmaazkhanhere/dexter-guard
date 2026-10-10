"""Stable domain and transport-facing errors for source ingestion."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, StrictStr


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_TRANSCRIPT = "INVALID_TRANSCRIPT"
    INVALID_RESIDENT_TEST_ID = "INVALID_RESIDENT_TEST_ID"
    UNSUPPORTED_INPUT_TYPE = "UNSUPPORTED_INPUT_TYPE"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    SOURCE_VERSION_NOT_FOUND = "SOURCE_VERSION_NOT_FOUND"
    DUPLICATE_SOURCE_VERSION = "DUPLICATE_SOURCE_VERSION"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_SOURCE_SPAN = "INVALID_SOURCE_SPAN"


class SourceErrorPayload(BaseModel):
    """The documented structured error envelope."""

    model_config = ConfigDict(extra="forbid")

    code: StrictStr
    message: StrictStr
    field: StrictStr | None = None


class SourceError(Exception):
    """A deterministic, serializable domain failure."""

    def __init__(self, code: ErrorCode | str, message: str, field: str | None = None) -> None:
        self.code = ErrorCode(code)
        self.message = message
        self.field = field
        super().__init__(message)

    def payload(self) -> SourceErrorPayload:
        values: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.field is not None:
            values["field"] = self.field
        return SourceErrorPayload.model_validate(values)


def invalid_request(message: str, field: str | None = None) -> SourceError:
    return SourceError(ErrorCode.INVALID_REQUEST, message, field)
