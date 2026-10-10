"""Application service for revision-bound, fail-safe claim extraction."""

from __future__ import annotations

import inspect
import hashlib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from pydantic import ValidationError

from .models import (
    EvidenceSourceReference,
    ExtractionEmpty,
    ExtractionError,
    ExtractionErrorCode,
    ExtractionFailed,
    ExtractionResult,
    ExtractionSucceeded,
)
from .observability import ExtractionMetrics, InMemoryExtractionLogger
from .ports import NoteRevisionReader
from .provider import (
    MalformedProviderOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    parse_provider_output,
    provider_metadata,
)
from .repository import ClaimRepository, InMemoryClaimRepository
from .revision_reader import NoteRevisionContext, RevisionReaderError
from .validator import ClaimValidationError, InvalidClaimSpanError, validate_claims


MAX_NOTE_CODE_POINTS = 50_000
DEFAULT_EXTRACTOR_VERSION = "claim-extractor-v1"
DEFAULT_SCHEMA_VERSION = "claim-extraction-v1"
DEFAULT_PROMPT_VERSION = "claim-extraction-v1"


class ClaimExtractionService:
    def __init__(
        self,
        revision_reader: NoteRevisionReader,
        provider: object,
        *,
        repository: ClaimRepository | None = None,
        extractor_version: str = DEFAULT_EXTRACTOR_VERSION,
        output_schema_version: str = DEFAULT_SCHEMA_VERSION,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        provider_timeout_seconds: float = 30.0,
        max_provider_attempts: int = 2,
        metrics: ExtractionMetrics | None = None,
        logger: object | None = None,
    ) -> None:
        if provider_timeout_seconds <= 0:
            raise ValueError("provider_timeout_seconds must be positive")
        if max_provider_attempts < 1:
            raise ValueError("max_provider_attempts must be positive")
        self.revision_reader = revision_reader
        self.provider = provider
        self.repository = repository or InMemoryClaimRepository()
        self.extractor_version = extractor_version
        self.output_schema_version = output_schema_version
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.provider_timeout_seconds = provider_timeout_seconds
        self.max_provider_attempts = max_provider_attempts
        self.metrics = metrics or ExtractionMetrics()
        self.logger = logger or InMemoryExtractionLogger()

    def extract_claims(
        self,
        note_revision_id: str,
        *,
        note_body: str | None = None,
        extraction_run_id: str | None = None,
    ) -> ExtractionResult:
        run_id = extraction_run_id or f"extraction-{self._id_factory()}"
        metadata = provider_metadata(self.provider)
        context: NoteRevisionContext | Any | None = None

        try:
            context = self._read_context(note_revision_id)
        except RevisionReaderError as error:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode(error.code),
                    str(error),
                    retryable=False,
                    note_revision_id=note_revision_id if error.code != "REVISION_NOT_FOUND" else None,
                    provider_metadata=metadata,
                )
            )
        except (KeyError, LookupError):
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.REVISION_NOT_FOUND,
                    "The requested note revision does not exist.",
                    retryable=False,
                    note_revision_id=None,
                    provider_metadata=metadata,
                )
            )
        except Exception:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.REVISION_MISMATCH,
                    "The immutable note revision could not be resolved.",
                    retryable=False,
                    note_revision_id=note_revision_id,
                    provider_metadata=metadata,
                )
            )

        try:
            context = self._normalise_context(context, note_revision_id)
        except RevisionReaderError as error:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode(error.code),
                    str(error),
                    retryable=False,
                    note_revision_id=note_revision_id,
                    provider_metadata=metadata,
                )
            )
        except (AttributeError, TypeError, ValidationError, ValueError):
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.REVISION_MISMATCH,
                    "The immutable note revision metadata is invalid.",
                    retryable=False,
                    note_revision_id=note_revision_id,
                    provider_metadata=metadata,
                )
            )
        if note_body is not None and note_body != context.note_body:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.REVISION_MISMATCH,
                    "The supplied note body does not match the immutable note revision.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )
        if context.language != "de-DE":
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.UNSUPPORTED_LANGUAGE,
                    "Only German candidate-note revisions are supported.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )
        if context.note_body_hash != hashlib.sha256(context.note_body.encode("utf-8")).hexdigest():
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.REVISION_MISMATCH,
                    "The immutable note body hash does not match the stored note text.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )
        if not context.synthetic or not context.resident_test_id:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.NON_SYNTHETIC_INPUT,
                    "The note revision is missing its synthetic resident association.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )
        if len(context.note_body) > MAX_NOTE_CODE_POINTS:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.REQUEST_TOO_LARGE,
                    "The note revision exceeds the maximum supported size.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )

        raw_output, provider_failure = self._invoke_provider(context.note_body, run_id, metadata)
        if provider_failure is not None:
            return self._finish(self._failed(run_id, *provider_failure, context=context, provider_metadata=metadata))
        try:
            raw_claims = parse_provider_output(raw_output)
        except MalformedProviderOutputError as error:
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.MALFORMED_PROVIDER_OUTPUT,
                    str(error),
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )
        try:
            claims = validate_claims(raw_claims, context)
        except InvalidClaimSpanError:
            self.metrics.increment("validation_failures")
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.INVALID_SPAN,
                    "The provider output contains a span that does not match the immutable note.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )
        except (ClaimValidationError, ValidationError, TypeError, ValueError):
            self.metrics.increment("validation_failures")
            return self._finish(
                self._failed(
                    run_id,
                    ExtractionErrorCode.INVALID_SCHEMA,
                    "The provider output did not satisfy the claim contract.",
                    retryable=False,
                    context=context,
                    provider_metadata=metadata,
                )
            )

        if not claims:
            if self._possible_assertion(context.note_body):
                self.metrics.increment("validation_failures")
                return self._finish(
                    self._failed(
                        run_id,
                        ExtractionErrorCode.INTERNAL_VALIDATION_ERROR,
                        "The provider returned no claims for text that may contain an assertion.",
                        retryable=False,
                        context=context,
                        provider_metadata=metadata,
                    )
                )
            result: ExtractionResult = ExtractionEmpty(
                extractionRunId=run_id,
                noteRevisionId=context.note_revision_id,
                noteBodyHash=context.note_body_hash,
                evidenceSourceReference=context.source_reference,
                extractorVersion=self.extractor_version,
                providerVersion=metadata["provider_version"],
                modelVersion=metadata["model_version"],
                promptVersion=metadata["prompt_version"],
                outputSchemaVersion=self.output_schema_version,
                claims=(),
                extractedAt=self._clock(),
            )
            self.metrics.increment("empty_results")
            return self._finish(result)

        result = ExtractionSucceeded(
            extractionRunId=run_id,
            noteRevisionId=context.note_revision_id,
            noteBodyHash=context.note_body_hash,
            evidenceSourceReference=context.source_reference,
            extractorVersion=self.extractor_version,
            providerVersion=metadata["provider_version"],
            modelVersion=metadata["model_version"],
            promptVersion=metadata["prompt_version"],
            outputSchemaVersion=self.output_schema_version,
            claims=claims,
            extractedAt=self._clock(),
        )
        self.metrics.increment("successful_results")
        return self._finish(result)

    extract = extract_claims

    def get_current_result(self, note_revision_id: str) -> ExtractionResult | None:
        return self.repository.get_current_result(note_revision_id, self.extractor_version)

    def _read_context(self, note_revision_id: str) -> object:
        return self.revision_reader.read(note_revision_id)

    @staticmethod
    def _normalise_context(context: object, requested_id: str) -> NoteRevisionContext:
        if isinstance(context, NoteRevisionContext):
            if context.note_revision_id != requested_id:
                raise RevisionReaderError("REVISION_MISMATCH", "The reader returned a different note revision.")
            return context
        source_reference = getattr(context, "source_reference", None)
        if isinstance(source_reference, Mapping):
            source_reference = EvidenceSourceReference.model_validate(source_reference)
        elif not isinstance(source_reference, EvidenceSourceReference):
            source_reference = EvidenceSourceReference.model_validate(source_reference)
        note_revision = getattr(context, "note_revision_id")
        if note_revision != requested_id:
            raise RevisionReaderError("REVISION_MISMATCH", "The reader returned a different note revision.")
        return NoteRevisionContext(
            note_revision_id=note_revision,
            note_body=getattr(context, "note_body"),
            note_body_hash=getattr(context, "note_body_hash"),
            resident_test_id=getattr(context, "resident_test_id"),
            language=getattr(context, "language"),
            synthetic=getattr(context, "synthetic"),
            source_reference=source_reference,
        )

    def _invoke_provider(
        self, note_text: str, run_id: str, metadata: dict[str, str | None]
    ) -> tuple[object | None, tuple[ExtractionErrorCode, str, bool] | None]:
        method = getattr(self.provider, "extract", None) or getattr(self.provider, "extract_claims", None)
        if method is None and callable(self.provider):
            method = self.provider
        if method is None:
            return None, (ExtractionErrorCode.PROVIDER_UNAVAILABLE, "No claim extraction provider is configured.", True)

        last_failure: tuple[ExtractionErrorCode, str, bool] = (
            ExtractionErrorCode.PROVIDER_UNAVAILABLE,
            "The claim extraction provider failed.",
            True,
        )
        for _ in range(self.max_provider_attempts):
            self.metrics.increment("provider_attempts")
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self._call_provider, method, note_text, run_id, metadata)
            timed_out = False
            try:
                return future.result(timeout=self.provider_timeout_seconds), None
            except (FutureTimeoutError, TimeoutError, ProviderTimeoutError):
                timed_out = True
                future.cancel()
                last_failure = (
                    ExtractionErrorCode.PROVIDER_TIMEOUT,
                    "The claim extraction provider exceeded its configured timeout.",
                    True,
                )
            except ProviderUnavailableError as error:
                last_failure = (ExtractionErrorCode.PROVIDER_UNAVAILABLE, str(error), True)
            except Exception:
                last_failure = (
                    ExtractionErrorCode.PROVIDER_UNAVAILABLE,
                    "The claim extraction provider failed.",
                    True,
                )
            finally:
                executor.shutdown(wait=not timed_out, cancel_futures=True)
        self.metrics.increment("provider_failures")
        return None, last_failure

    @staticmethod
    def _call_provider(method: Callable[..., object], note_text: str, run_id: str, metadata: dict[str, str | None]) -> object:
        parameters = inspect.signature(method).parameters
        kwargs: dict[str, object] = {}
        if "extraction_run_id" in parameters:
            kwargs["extraction_run_id"] = run_id
        if "prompt_version" in parameters:
            kwargs["prompt_version"] = metadata["prompt_version"] or DEFAULT_PROMPT_VERSION
        return method(note_text, **kwargs)

    @staticmethod
    def _possible_assertion(note_text: str) -> bool:
        import re

        cleaned = re.sub(r"[\W_]+", " ", note_text, flags=re.UNICODE).strip().casefold()
        if not cleaned:
            return False
        if cleaned in {"hallo", "guten morgen", "guten tag", "guten abend", "danke"}:
            return False
        if re.search(r"\b(?:ist|sind|hat|haben|wurde|wurden|berichtet|trank|isst|schmerz|fieber|temperatur|medikament)\b", cleaned):
            return True
        return len(cleaned.split()) >= 2

    def _finish(self, result: ExtractionResult) -> ExtractionResult:
        try:
            persisted = self.repository.save(result)
        except Exception:
            # Persistence errors are not allowed to turn a validated claim into an
            # untracked success; retain the typed failure shape and no claims.
            if result.status.value in {"SUCCEEDED", "EMPTY"}:
                persisted = self._failed(
                    result.extraction_run_id,
                    ExtractionErrorCode.INTERNAL_VALIDATION_ERROR,
                    "The extraction result could not be persisted.",
                    retryable=True,
                    note_revision_id=getattr(result, "note_revision_id", None),
                    provider_metadata={
                        "provider_version": result.provider_version,
                        "model_version": result.model_version,
                        "prompt_version": result.prompt_version,
                    },
                )
                self.repository.save(persisted)
            else:
                persisted = result
        self.logger.event("claim_extraction_completed", status=persisted.status.value, error_code=getattr(getattr(persisted, "error", None), "code", None))
        return persisted

    def _failed(
        self,
        run_id: str,
        code: ExtractionErrorCode,
        message: str,
        retryable: bool,
        *,
        context: NoteRevisionContext | None = None,
        note_revision_id: str | None = None,
        provider_metadata: dict[str, str | None] | None = None,
    ) -> ExtractionFailed:
        metadata = provider_metadata or {}
        return ExtractionFailed(
            extractionRunId=run_id,
            noteRevisionId=context.note_revision_id if context is not None else note_revision_id,
            noteBodyHash=context.note_body_hash if context is not None else None,
            extractorVersion=self.extractor_version,
            providerVersion=metadata.get("provider_version"),
            modelVersion=metadata.get("model_version"),
            promptVersion=metadata.get("prompt_version"),
            outputSchemaVersion=self.output_schema_version,
            claims=(),
            error=ExtractionError(code=code, message=message, retryable=retryable),
            extractedAt=self._clock(),
        )
