"""Application services for generated and externally imported note drafts."""

from __future__ import annotations

import hashlib
import inspect
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ProviderTimeoutError
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ValidationError

from .adapters import GenerationAdapter, UnavailableGenerationAdapter
from .contracts import (
    CandidateNursingFact,
    GenerateRequest,
    GenerationResult,
    ImportRequest,
    NoteResponse,
    NoteRevisionRecord,
    NursingFact,
)
from .errors import NoteError, NoteErrorCode
from .guardrails import GenerationGuardrails
from .observability import GenerationMetrics
from .repository import NoteRepository, SQLiteNoteRepository

if TYPE_CHECKING:
    from source_ingestion.contracts import SourceDocument


class NursingNoteService:
    """Coordinates source resolution, provider validation, and note persistence."""

    def __init__(
        self,
        source_service: object,
        *,
        repository: NoteRepository | None = None,
        generation_adapter: GenerationAdapter | None = None,
        guardrails: GenerationGuardrails | None = None,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        provider_timeout_seconds: float = 30.0,
        max_provider_attempts: int = 2,
        metrics: GenerationMetrics | None = None,
    ) -> None:
        if provider_timeout_seconds <= 0:
            raise ValueError("provider_timeout_seconds must be positive")
        if max_provider_attempts < 1:
            raise ValueError("max_provider_attempts must be positive")
        self.source_service = source_service
        self.repository = repository or SQLiteNoteRepository()
        self.generation_adapter = generation_adapter or UnavailableGenerationAdapter()
        self.guardrails = guardrails or GenerationGuardrails()
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.provider_timeout_seconds = provider_timeout_seconds
        self.max_provider_attempts = max_provider_attempts
        self.metrics = metrics or GenerationMetrics()

    def generate(self, payload: GenerateRequest | Mapping[str, object]) -> NoteResponse:
        request = self._parse_request(payload, GenerateRequest, "generate")
        source = self._resolve_source(request.source_id, request.source_version)
        validation_run_id = f"validation-{self._id_factory()}"
        generation_run_id = f"generation-{self._id_factory()}"
        try:
            raw_result = self._invoke_provider(source, generation_run_id)
            result = self._validate_generation_result(raw_result)
            self.guardrails.validate(result, source)
        except NoteError as error:
            if error.code in {
                NoteErrorCode.GENERATION_REJECTED,
                NoteErrorCode.EMPTY_MODEL_OUTPUT,
            }:
                self.metrics.increment("generation_rejections")
            raise
        note_id = f"note-{self._id_factory()}"
        facts = self._persisted_facts(
            result.facts,
            note_id=note_id,
            revision=1,
        )
        now = self._clock()
        record = NoteRevisionRecord(
            noteId=note_id,
            revision=1,
            content=result.content,
            status="DRAFT",
            origin="GENERATED",
            sourceId=source.source_id,
            sourceVersion=source.source_version,
            validationRunId=validation_run_id,
            facts=tuple(facts),
            generationRunId=generation_run_id,
            modelId=result.model_id,
            promptVersion=result.prompt_version,
            schemaVersion=result.schema_version or self.guardrails.schema_version,
            rulesetVersion=result.ruleset_version or self.guardrails.ruleset_version,
            sourceTextHash=self._source_hash(source),
            normalizationPolicy=self.guardrails.normalization_policy,
            createdAt=now,
            createdBy=request.requested_by,
        )
        response = self.repository.create(record).response()
        self.metrics.increment("successful_generations")
        return response

    def import_note(self, payload: ImportRequest | Mapping[str, object]) -> NoteResponse:
        request = self._parse_request(payload, ImportRequest, "import")
        self.metrics.increment("imports")
        source = self._resolve_source(request.source_id, request.source_version)
        self._validate_external_facts(request.facts, source)
        note_id = f"note-{self._id_factory()}"
        facts = self._persisted_facts(request.facts, note_id=note_id, revision=1)
        record = NoteRevisionRecord(
            noteId=note_id,
            revision=1,
            content=request.content,
            status="DRAFT",
            origin="IMPORTED",
            sourceId=source.source_id,
            sourceVersion=source.source_version,
            externalOrigin=request.external_origin,
            validationRunId=f"validation-{self._id_factory()}",
            facts=tuple(facts),
            schemaVersion="nursing-fact-v1",
            rulesetVersion="import-no-inference-v1",
            sourceTextHash=self._source_hash(source),
            normalizationPolicy=self.guardrails.normalization_policy,
            createdAt=self._clock(),
            createdBy=request.requested_by,
        )
        return self.repository.create(record).response()

    def create_revision(
        self,
        note_id: str,
        content: str,
        *,
        expected_revision: int,
        requested_by: str,
    ) -> NoteResponse:
        """Create an editable predecessor-linked draft for the downstream editor."""
        if not content or not content.strip():
            raise NoteError(NoteErrorCode.INVALID_NOTE_REQUEST, "content must not be blank.", "content")
        previous = self.repository.get(note_id, expected_revision)
        revision = previous.revision + 1
        facts = tuple(
            fact.model_copy(update={"revision": revision, "fact_id": f"{note_id}:r{revision}:f{index}"})
            for index, fact in enumerate(previous.facts, start=1)
        )
        record = previous.model_copy(
            update={
                "revision": revision,
                "previous_revision_id": f"{note_id}:r{previous.revision}",
                "content": content,
                "facts": facts,
                "validation_run_id": f"validation-{self._id_factory()}",
                "created_at": self._clock(),
                "created_by": requested_by,
            }
        )
        return self.repository.create(record).response()

    def _resolve_source(self, source_id: str, source_version: int):
        return self.source_service.get_source_version(source_id, source_version)

    def _invoke_provider(self, source: object, generation_run_id: str) -> object:
        """Invoke a provider with bounded attempts and timeout using one stable run ID."""
        last_error: NoteError | None = None
        for _ in range(self.max_provider_attempts):
            self.metrics.increment("provider_attempts")
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self._call_adapter, source, generation_run_id)
            try:
                return future.result(timeout=self.provider_timeout_seconds)
            except ProviderTimeoutError as error:
                future.cancel()
                last_error = NoteError(
                    NoteErrorCode.GENERATION_PROVIDER_TIMEOUT,
                    "The generation provider exceeded its configured timeout.",
                )
            except NoteError as error:
                last_error = error
            except Exception as error:  # provider-specific failures must not leak
                last_error = NoteError(
                    NoteErrorCode.GENERATION_PROVIDER_FAILURE,
                    "The generation provider failed.",
                )
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        self.metrics.increment("provider_failures")
        if last_error is not None:
            raise last_error
        raise NoteError(NoteErrorCode.GENERATION_PROVIDER_FAILURE, "The generation provider failed.")

    def _call_adapter(self, source: object, generation_run_id: str) -> object:
        method = self.generation_adapter.generate
        parameters = inspect.signature(method).parameters
        if "generation_run_id" in parameters:
            return method(source, generation_run_id=generation_run_id)
        return method(source)

    @staticmethod
    def _parse_request(payload: object, model: type[GenerateRequest] | type[ImportRequest], operation: str):
        if isinstance(payload, model):
            return payload
        try:
            return model.model_validate(payload)
        except ValidationError as error:
            first = error.errors()[0] if error.errors() else {}
            field = ".".join(str(part) for part in first.get("loc", ())) or None
            raise NoteError(
                NoteErrorCode.INVALID_NOTE_REQUEST,
                f"The {operation} request does not match the notes contract.",
                field,
            ) from error

    @staticmethod
    def _validate_generation_result(raw_result: object) -> GenerationResult:
        if isinstance(raw_result, Mapping) and "content" in raw_result:
            content = raw_result.get("content")
            if isinstance(content, str) and not content.strip():
                raise NoteError(NoteErrorCode.EMPTY_MODEL_OUTPUT, "The generation provider returned empty note content.")
        try:
            result = raw_result if isinstance(raw_result, GenerationResult) else GenerationResult.model_validate(raw_result)
        except (ValidationError, TypeError, ValueError) as error:
            raise NoteError(
                NoteErrorCode.GENERATION_REJECTED,
                "The generation provider returned malformed or schema-invalid output.",
            ) from error
        if not result.content.strip():
            raise NoteError(NoteErrorCode.EMPTY_MODEL_OUTPUT, "The generation provider returned empty note content.")
        return result

    @staticmethod
    def _validate_external_facts(facts: tuple[CandidateNursingFact, ...], source: SourceDocument) -> None:
        for index, fact in enumerate(facts):
            if fact.provenance != "EXTERNALLY_SUPPLIED":
                raise NoteError(
                    NoteErrorCode.INVALID_NOTE_REQUEST,
                    "Imported facts must use EXTERNALLY_SUPPLIED provenance.",
                    f"facts.{index}.provenance",
                )
            if fact.resident_subject not in {source.resident_test_id, "UNKNOWN"}:
                raise NoteError(
                    NoteErrorCode.INVALID_NOTE_REQUEST,
                    "An imported fact names an unsupported resident subject.",
                    f"facts.{index}.residentSubject",
                )
            anchor = fact.source_anchor
            if anchor.source_id is not None and (
                anchor.source_id != source.source_id or anchor.source_version != source.source_version
            ):
                raise NoteError(
                    NoteErrorCode.INVALID_NOTE_REQUEST,
                    "An imported fact references a different evidence source.",
                    f"facts.{index}.sourceAnchor",
                )

    @staticmethod
    def _persisted_facts(
        facts: tuple[CandidateNursingFact, ...], *, note_id: str, revision: int
    ) -> list[NursingFact]:
        return [
            NursingFact.model_validate(
                fact.model_dump()
                | {
                    "factId": f"{note_id}:r{revision}:f{index}",
                    "noteId": note_id,
                    "revision": revision,
                }
            )
            for index, fact in enumerate(facts, start=1)
        ]

    @staticmethod
    def _source_hash(source: SourceDocument) -> str:
        return hashlib.sha256(source.transcript_text.encode("utf-8")).hexdigest()
