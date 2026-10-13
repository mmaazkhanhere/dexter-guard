"""Stable errors for the Spec 005 service and API boundary."""

from __future__ import annotations

from typing import Any

from .contracts import ApiError, ApiErrorCode, SchemaError


class DeterministicValidationError(RuntimeError):
    """A safe, typed failure that must not produce a partial validation run."""

    def __init__(self, payload: ApiError | SchemaError, status_code: int) -> None:
        super().__init__(payload.message)
        self.payload = payload
        self.status_code = status_code


def schema_error(message: str, path: str | None = None) -> DeterministicValidationError:
    return DeterministicValidationError(SchemaError(code="SCHEMA_ERROR", message=message, path=path), 422)


def api_error(code: ApiErrorCode, message: str, status_code: int) -> DeterministicValidationError:
    return DeterministicValidationError(ApiError(code=code, message=message), status_code)


def map_repository_error(error: Exception, *, kind: str, identifier: str) -> DeterministicValidationError:
    """Map repository failures without leaking storage details."""

    if isinstance(error, KeyError):
        code = {
            "source": ApiErrorCode.SOURCE_NOT_FOUND,
            "source_fact": ApiErrorCode.SOURCE_FACT_NOT_FOUND,
            "claim": ApiErrorCode.CLAIM_NOT_FOUND,
            "alignment": ApiErrorCode.ALIGNMENT_NOT_FOUND,
        }.get(kind, ApiErrorCode.INTERNAL_ERROR)
        return api_error(code, f"The requested {kind} record was not found: {identifier}.", 404)
    if isinstance(error, LookupError):
        code = ApiErrorCode.SOURCE_VERSION_NOT_FOUND if kind == "source_version" else ApiErrorCode.SOURCE_NOT_FOUND
        return api_error(code, f"The requested {kind} was not found.", 404)
    return api_error(ApiErrorCode.DEPENDENCY_UNAVAILABLE, "A required validation repository is unavailable.", 503)


__all__ = ["DeterministicValidationError", "api_error", "map_repository_error", "schema_error"]

