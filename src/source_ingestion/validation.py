"""Strict request validation at the source-ingestion boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .contracts import CreateSourceRequest, CreateSourceVersionRequest, SourceSpan
from .errors import ErrorCode, SourceError


ModelT = TypeVar("ModelT", bound=BaseModel)


def _field_path(location: tuple[Any, ...]) -> str | None:
    parts = [str(part) for part in location if part not in ("body",)]
    return ".".join(parts) if parts else None


def _map_validation_error(error: ValidationError, *, version_request: bool = False) -> SourceError:
    first = error.errors()[0] if error.errors() else {}
    field = _field_path(tuple(first.get("loc", ())))
    error_type = first.get("type")
    if error_type == "extra_forbidden":
        code = ErrorCode.INVALID_REQUEST
        message = "The request contains a field that is not part of the source contract."
    elif field == "transcript_text":
        code = ErrorCode.INVALID_TRANSCRIPT
        message = "transcript_text must be a non-blank string."
    elif field == "resident_test_id":
        code = ErrorCode.INVALID_RESIDENT_TEST_ID
        message = "resident_test_id must be exactly one valid scalar synthetic-resident ID."
    else:
        code = ErrorCode.INVALID_REQUEST
        message = "The request does not match the source contract."
    if version_request and field == "expected_source_version":
        message = "expected_source_version must be a positive integer."
    return SourceError(code, message, field)


def _require_object(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise SourceError(ErrorCode.INVALID_REQUEST, "The request body must be a JSON object.")
    return payload


def _reject_unsupported_input(payload: Mapping[str, Any]) -> None:
    unsupported_fields = {"audio", "audio_url", "audio_data", "audio_file", "audio_bytes"}
    present = unsupported_fields.intersection(payload.keys())
    if present:
        field = sorted(present)[0]
        raise SourceError(
            ErrorCode.UNSUPPORTED_INPUT_TYPE,
            "Audio and other non-text input types are not supported.",
            field,
        )


def validate_create_source_request(payload: Any) -> CreateSourceRequest:
    body = _require_object(payload)
    _reject_unsupported_input(body)
    try:
        return CreateSourceRequest.model_validate(body)
    except ValidationError as error:
        raise _map_validation_error(error) from error


def validate_create_source_version_request(payload: Any) -> CreateSourceVersionRequest:
    body = _require_object(payload)
    _reject_unsupported_input(body)
    try:
        return CreateSourceVersionRequest.model_validate(body)
    except ValidationError as error:
        raise _map_validation_error(error, version_request=True) from error


def validate_source_span(payload: Any) -> SourceSpan:
    body = _require_object(payload)
    try:
        return SourceSpan.model_validate(body)
    except ValidationError as error:
        first = error.errors()[0] if error.errors() else {}
        field = _field_path(tuple(first.get("loc", ())))
        raise SourceError(
            ErrorCode.INVALID_SOURCE_SPAN,
            "The source span does not match the source-span contract.",
            field,
        ) from error
