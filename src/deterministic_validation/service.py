"""Application service for deterministic validation runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from .contracts import (
    Alignment,
    Claim,
    ENGINE_VERSION,
    SourceFact,
    TranscriptSnapshot,
    ValidationRequest,
    ValidationRun,
    CONTRACT_VERSION,
    RULESET_VERSION,
)
from .engine import DeterministicRuleEngine
from .errors import DeterministicValidationError, api_error, map_repository_error, schema_error
from .repository import (
    AlignmentRepository,
    ClaimRepository,
    SourceFactRepository,
    TranscriptRepository,
    ValidationRunRepository,
)
from .observability import ValidationTelemetry


def _plain_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True, mode="json")
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return value


def _canonical_digest(request: ValidationRequest, snapshot: TranscriptSnapshot, facts: tuple[SourceFact, ...],
                      claims: tuple[Claim, ...], alignments: tuple[Alignment, ...]) -> str:
    payload = {
        "request": request.model_dump(by_alias=True, mode="json"),
        "snapshot": snapshot.model_dump(by_alias=True, mode="json"),
        "facts": [item.model_dump(by_alias=True, mode="json") for item in facts],
        "claims": [item.model_dump(by_alias=True, mode="json") for item in claims],
        "alignments": [item.model_dump(by_alias=True, mode="json") for item in alignments],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class DeterministicValidationService:
    """Resolve immutable records, run pure rules, and append one complete result."""

    def __init__(
        self,
        transcript_repository: TranscriptRepository,
        source_fact_repository: SourceFactRepository,
        claim_repository: ClaimRepository,
        alignment_repository: AlignmentRepository,
        run_repository: ValidationRunRepository,
        *,
        engine: DeterministicRuleEngine | None = None,
        id_factory: Callable[[], str] | None = None,
        engine_version: str = ENGINE_VERSION,
        telemetry: ValidationTelemetry | None = None,
    ) -> None:
        self.transcript_repository = transcript_repository
        self.source_fact_repository = source_fact_repository
        self.claim_repository = claim_repository
        self.alignment_repository = alignment_repository
        self.run_repository = run_repository
        self.engine = engine or DeterministicRuleEngine()
        self._id_factory = id_factory or (lambda: f"validation-{uuid4()}")
        self.engine_version = engine_version
        self.telemetry = telemetry

    def _snapshot(self, request: ValidationRequest) -> TranscriptSnapshot:
        try:
            raw = self.transcript_repository.get(request.source_id, request.source_version)
        except Exception as error:
            code = getattr(getattr(error, "code", None), "value", getattr(error, "code", None))
            if code == "SOURCE_NOT_FOUND":
                raise api_error(code="SOURCE_NOT_FOUND", message="The requested source does not exist.", status_code=404) from error
            if code == "SOURCE_VERSION_NOT_FOUND":
                raise api_error(code="SOURCE_VERSION_NOT_FOUND", message="The requested source version does not exist.", status_code=404) from error
            raise map_repository_error(error, kind="source_version", identifier=request.source_id) from error
        try:
            snapshot = TranscriptSnapshot.model_validate(_plain_payload(raw))
        except ValidationError as error:
            raise api_error(code="PROVENANCE_CONFLICT", message="The resolved source snapshot is malformed.", status_code=409) from error
        if (snapshot.source_id, snapshot.source_version) != (request.source_id, request.source_version):
            raise api_error(code="PROVENANCE_CONFLICT", message="Resolved source identity conflicts with the request.", status_code=409)
        return snapshot

    @staticmethod
    def _record_error(error: Exception, *, kind: str, identifier: str) -> DeterministicValidationError:
        return map_repository_error(error, kind=kind, identifier=identifier)

    def _resolve_fact(self, request: ValidationRequest, fact_id: str) -> SourceFact:
        try:
            raw = self.source_fact_repository.get(fact_id)
        except Exception as error:
            raise self._record_error(error, kind="source_fact", identifier=fact_id) from error
        try:
            fact = SourceFact.model_validate(_plain_payload(raw))
        except ValidationError as error:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Source fact {fact_id} is malformed or unsupported.", status_code=409) from error
        if fact.source_fact_id != fact_id or (fact.source_id, fact.source_version) != (request.source_id, request.source_version):
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Source fact {fact_id} conflicts with the requested source.", status_code=409)
        return fact

    def _resolve_claim(self, request: ValidationRequest, claim_id: str) -> Claim:
        try:
            raw = self.claim_repository.get(claim_id)
        except Exception as error:
            raise self._record_error(error, kind="claim", identifier=claim_id) from error
        try:
            claim = Claim.model_validate(_plain_payload(raw))
        except ValidationError as error:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Claim {claim_id} is malformed or unsupported.", status_code=409) from error
        if claim.claim_id != claim_id or claim.note_id != request.note_id:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Claim {claim_id} conflicts with the requested note.", status_code=409)
        if claim.note_revision is not None and claim.note_revision != request.note_revision:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Claim {claim_id} conflicts with the requested note revision.", status_code=409)
        return claim

    def _resolve_alignment(self, request: ValidationRequest, alignment_id: str) -> Alignment:
        try:
            raw = self.alignment_repository.get(alignment_id)
        except Exception as error:
            raise self._record_error(error, kind="alignment", identifier=alignment_id) from error
        try:
            alignment = Alignment.model_validate(_plain_payload(raw))
        except ValidationError as error:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Alignment {alignment_id} is malformed or unsupported.", status_code=409) from error
        if alignment.alignment_id != alignment_id:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Alignment {alignment_id} has an inconsistent identity.", status_code=409)
        if alignment.source_fact_id not in request.source_fact_ids or alignment.claim_id not in request.claim_ids:
            raise api_error(code="PROVENANCE_CONFLICT", message=f"Alignment {alignment_id} references an unselected record.", status_code=409)
        return alignment

    def execute(self, payload: ValidationRequest | Mapping[str, Any]) -> ValidationRun:
        if isinstance(payload, ValidationRequest):
            request = payload
        else:
            try:
                request = ValidationRequest.model_validate(payload)
            except ValidationError as error:
                first = error.errors()[0] if error.errors() else {}
                location = ".".join(str(item) for item in first.get("loc", ())) or None
                raise schema_error("The request does not match the deterministic validation contract.", location) from error

        snapshot = self._snapshot(request)
        facts = tuple(self._resolve_fact(request, item) for item in request.source_fact_ids)
        claims = tuple(self._resolve_claim(request, item) for item in request.claim_ids)
        alignments = tuple(self._resolve_alignment(request, item) for item in request.alignment_ids)
        try:
            findings = self.engine.evaluate(snapshot, facts, claims, alignments)
            run = ValidationRun(
                validation_run_id=str(self._id_factory()),
                source_id=request.source_id,
                source_version=request.source_version,
                note_id=request.note_id,
                note_revision=request.note_revision,
                input_digest=_canonical_digest(request, snapshot, facts, claims, alignments),
                engine_version=self.engine_version,
                contract_version=CONTRACT_VERSION,
                ruleset_version=RULESET_VERSION,
                findings=findings,
            )
        except DeterministicValidationError:
            raise
        except Exception as error:
            raise api_error(code="INTERNAL_ERROR", message="Deterministic validation could not complete.", status_code=500) from error
        try:
            persisted = self.run_repository.append(run)
            if self.telemetry is not None:
                self.telemetry.record(persisted)
            return persisted
        except DeterministicValidationError:
            raise
        except Exception as error:
            raise api_error(code="DEPENDENCY_UNAVAILABLE", message="The validation run repository is unavailable.", status_code=503) from error


__all__ = ["DeterministicValidationService"]

