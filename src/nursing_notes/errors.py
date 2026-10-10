"""Stable errors for note generation and external-note import."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, StrictStr


class NoteErrorCode(StrEnum):
    INVALID_NOTE_REQUEST = "INVALID_NOTE_REQUEST"
    GENERATION_REJECTED = "GENERATION_REJECTED"
    EMPTY_MODEL_OUTPUT = "EMPTY_MODEL_OUTPUT"
    GENERATION_PROVIDER_UNAVAILABLE = "GENERATION_PROVIDER_UNAVAILABLE"
    GENERATION_PROVIDER_FAILURE = "GENERATION_PROVIDER_FAILURE"
    NOTE_NOT_FOUND = "NOTE_NOT_FOUND"
    NOTE_VERSION_CONFLICT = "NOTE_VERSION_CONFLICT"


class NoteErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: StrictStr
    message: StrictStr
    field: StrictStr | None = None


class NoteError(Exception):
    """A typed failure that is safe to expose at the API boundary."""

    def __init__(self, code: NoteErrorCode | str, message: str, field: str | None = None) -> None:
        self.code = NoteErrorCode(code)
        self.message = message
        self.field = field
        super().__init__(message)

    def payload(self) -> NoteErrorPayload:
        values: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.field is not None:
            values["field"] = self.field
        return NoteErrorPayload.model_validate(values)
