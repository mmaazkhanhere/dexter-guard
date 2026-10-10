"""FastAPI demo boundary for the source-ingestion contracts."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from .contracts import ResolvedSourceSpan, SourceDocument
from .errors import ErrorCode, SourceError
from .service import SourceIngestionService


class _DuplicateJsonKey(ValueError):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"duplicate JSON key: {key}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(key)
        result[key] = value
    return result


async def _json_object(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise SourceError(
            ErrorCode.UNSUPPORTED_INPUT_TYPE,
            "Only application/json text requests are supported.",
            "content-type",
        )
    raw = await request.body()
    if not raw:
        raise SourceError(ErrorCode.INVALID_REQUEST, "The request body must not be empty.")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except UnicodeDecodeError as error:
        raise SourceError(ErrorCode.INVALID_REQUEST, "The request body must be valid UTF-8.") from error
    except _DuplicateJsonKey as error:
        code = ErrorCode.INVALID_RESIDENT_TEST_ID if error.key == "resident_test_id" else ErrorCode.INVALID_REQUEST
        raise SourceError(code, "The request contains a repeated field.", error.key) from error
    except json.JSONDecodeError as error:
        raise SourceError(ErrorCode.INVALID_REQUEST, "The request body must be valid JSON.") from error
    if not isinstance(payload, dict):
        raise SourceError(ErrorCode.INVALID_REQUEST, "The request body must be a JSON object.")
    return payload


def _status_for_error(error: SourceError) -> int:
    if error.code == ErrorCode.UNSUPPORTED_INPUT_TYPE:
        return status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    if error.code in {ErrorCode.SOURCE_NOT_FOUND, ErrorCode.SOURCE_VERSION_NOT_FOUND}:
        return status.HTTP_404_NOT_FOUND
    if error.code == ErrorCode.VERSION_CONFLICT:
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


def _error_response(error: SourceError) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for_error(error),
        content=error.payload().model_dump(exclude_none=True),
    )


def _validation_error_response(error: RequestValidationError) -> JSONResponse:
    first = error.errors()[0] if error.errors() else {}
    location = first.get("loc", ())
    field = ".".join(str(item) for item in location if item not in {"path", "body"}) or None
    return _error_response(SourceError(ErrorCode.INVALID_REQUEST, "The request does not match the source contract.", field))


def create_app(service: SourceIngestionService | None = None) -> FastAPI:
    service = service or SourceIngestionService()
    app = FastAPI(title="Source and Note Ingestion API", version="1.0.0")
    app.state.source_service = service

    @app.exception_handler(SourceError)
    async def handle_source_error(_: Request, error: SourceError) -> JSONResponse:
        return _error_response(error)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        return _validation_error_response(error)

    @app.post("/sources", response_model=SourceDocument, status_code=status.HTTP_201_CREATED)
    async def create_source(request: Request) -> SourceDocument:
        return service.create_source(await _json_object(request))

    @app.post(
        "/sources/{source_id}/versions",
        response_model=SourceDocument,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_source_version(source_id: str, request: Request) -> SourceDocument:
        return service.create_source_version(source_id, await _json_object(request))

    @app.get(
        "/sources/{source_id}/versions/{source_version}",
        response_model=SourceDocument,
    )
    async def get_source_version(
        source_id: str,
        source_version: Annotated[int, Path(ge=1)],
    ) -> SourceDocument:
        return service.get_source_version(source_id, source_version)

    @app.post("/source-spans/resolve", response_model=ResolvedSourceSpan)
    async def resolve_source_span(request: Request) -> ResolvedSourceSpan:
        return service.resolve_span(await _json_object(request))

    return app


app = create_app()
