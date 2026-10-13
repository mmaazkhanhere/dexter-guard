"""Application service for immutable source-to-note coverage runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from claim_extraction.models import Claim
from pydantic import ValidationError

from source_ingestion.contracts import SourceDocument
from source_ingestion.errors import SourceError
from source_ingestion.repository import SourceRepository

from .contracts import (
    CoverageCounts,
    CoverageRunFailed,
    CoverageRunRequest,
    CoverageRunSucceeded,
    ExecutionMetrics,
    Failure,
    RelatedFindingRef,
    RunStatus,
)
from .extraction import (
    ExtractionIntegrityError,
    HeuristicGermanSourceFactExtractor,
    SourceFactExtractionResult,
    SourceFactExtractor,
    validate_source_span,
    source_text_hash,
)
from .matching import HeuristicGermanSemanticMatcher, RelatedFinding, SemanticCoverageMatcher, build_assessments
from .provider import BoundedSemanticMatcher, ProviderOutputError, ProviderTimeoutError
from .repository import (
    ClaimSetRecord,
    ClaimSetRepository,
    CoverageRunRepository,
    InMemoryCoverageRunRepository,
    InMemoryRelatedFindingRepository,
    InMemorySourceFactExtractionRepository,
    RelatedFindingRepository,
    SourceFactExtractionRepository,
)


class CoverageServiceError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class NoteRevisionRepository(Protocol):
    def get(self, note_id: str, revision: int) -> object: ...


def _digest(request: CoverageRunRequest) -> str:
    payload = request.model_dump(mode="json", by_alias=True)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SourceCoverageService:
    def __init__(
        self,
        source_repository: SourceRepository,
        extraction_repository: SourceFactExtractionRepository,
        claim_set_repository: ClaimSetRepository,
        run_repository: CoverageRunRepository | None = None,
        *,
        matcher: SemanticCoverageMatcher | None = None,
        related_finding_repository: RelatedFindingRepository | None = None,
        note_repository: NoteRevisionRepository | None = None,
        extractor: SourceFactExtractor | None = None,
        id_factory: Callable[[], str] | None = None,
        correlation_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.source_repository = source_repository
        self.extraction_repository = extraction_repository
        self.claim_set_repository = claim_set_repository
        self.run_repository = run_repository or InMemoryCoverageRunRepository()
        self.matcher = matcher or BoundedSemanticMatcher(lambda facts, claims, run_id: HeuristicGermanSemanticMatcher().match(facts, claims, run_id=run_id))
        self.related_finding_repository = related_finding_repository or InMemoryRelatedFindingRepository()
        self.note_repository = note_repository
        self.extractor = extractor or HeuristicGermanSourceFactExtractor()
        self._id_factory = id_factory or (lambda: f"coverage-run-{uuid4()}")
        self._correlation_factory = correlation_factory or (lambda: f"correlation-{uuid4()}")
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(self, payload: CoverageRunRequest | dict[str, Any]) -> CoverageRunSucceeded | CoverageRunFailed:
        try:
            request = payload if isinstance(payload, CoverageRunRequest) else CoverageRunRequest.model_validate(payload)
        except ValidationError as error:
            raise CoverageServiceError("SCHEMA_ERROR", str(error), 422) from error
        digest = _digest(request)
        try:
            existing = self.run_repository.get_by_idempotency(request.idempotency_key)
        except Exception as error:
            raise CoverageServiceError("DEPENDENCY_UNAVAILABLE", "The coverage run repository is unavailable.", 503) from error
        if existing is not None:
            if existing.input_digest != digest:
                raise CoverageServiceError("IDEMPOTENCY_KEY_CONFLICT", "The idempotency key is bound to another request.", 409)
            return existing
        created_at = self._clock()
        run_id = self._id_factory()
        correlation_id = self._correlation_factory()
        try:
            source = self.source_repository.get(request.source_id, request.source_version)
            extraction = self.extraction_repository.get(request.source_fact_extraction_run_id)
            claim_set = self.claim_set_repository.get(request.claim_set_id)
            self._validate_provenance(request, source, extraction, claim_set)
            if self.note_repository is not None:
                self.note_repository.get(request.note_id, request.note_revision)
            started_at = self._clock()
            claims = tuple(claim_set.claims)
            expected_facts = tuple(fact for fact in extraction.facts if fact.documentation_expectation.value != "CONTEXTUAL")
            source_quotes = {
                fact.source_fact_id: tuple(validate_source_span(span, source) for span in fact.source_spans)
                for fact in expected_facts
            }
            source_quotes.update({
                item.unresolved_source_item_id: tuple(validate_source_span(span, source) for span in item.candidate_source_spans)
                for item in extraction.unresolved_items
            })
            relations = self.matcher.match(expected_facts, claims, run_id=run_id)
            related = self.related_finding_repository.list(
                source_id=request.source_id, source_version=request.source_version,
                fact_ids=tuple(item.source_fact_id for item in expected_facts), claim_ids=tuple(item.id for item in claims),
            )
            refs_by_owner: dict[str, tuple[RelatedFindingRef, ...]] = {}
            relation_claims_by_fact: dict[str, set[str]] = {}
            for relation in relations:
                if relation.claim_id is not None:
                    relation_claims_by_fact.setdefault(relation.source_fact_id, set()).add(relation.claim_id)
            for owner in tuple(item.source_fact_id for item in expected_facts) + tuple(item.unresolved_source_item_id for item in extraction.unresolved_items):
                claim_ids_for_owner = relation_claims_by_fact.get(owner, set())
                refs = tuple(RelatedFindingRef(owner=item.owner, findingId=item.finding_id) for item in related if item.source_fact_id == owner or item.claim_id in claim_ids_for_owner)
                if refs:
                    refs_by_owner[owner] = refs
            assessments, findings = build_assessments(expected_facts, extraction.unresolved_items, relations, source_quotes=source_quotes, related_refs=refs_by_owner)
            counts = self._counts(assessments, expected_facts, extraction.unresolved_items)
            completed_at = self._clock()
            run = CoverageRunSucceeded(
                coverageRunId=run_id, status=RunStatus.SUCCEEDED, sourceId=request.source_id, sourceVersion=request.source_version,
                residentContext=request.resident_context, sourceTextHash=request.source_text_hash, normalizationPolicy=request.normalization_policy,
                noteId=request.note_id, noteRevision=request.note_revision, sourceFactExtractionRunId=request.source_fact_extraction_run_id,
                claimSetId=request.claim_set_id, rulesetVersion=request.ruleset_version, coverageStatusPolicyVersion="COVERAGE_STATUS-v1",
                expectationPolicyVersion="COVERAGE_EXPECTATION-v1", datasetVersion=request.dataset_version, idempotencyKey=request.idempotency_key,
                correlationId=correlation_id, providerVersion=getattr(self.matcher, "matcher_version", None), modelVersion=None, promptVersion=None,
                inputDigest=digest, assessments=assessments, findings=findings, runtimeCounts=counts,
                executionMetrics=ExecutionMetrics(latencyMilliseconds=max(0, int((completed_at - started_at).total_seconds() * 1000)), retryCount=getattr(self.matcher, "last_retry_count", 0), inputTokens=None, outputTokens=None, inferenceCost=None, warningCount=len(findings)),
                createdAt=created_at, startedAt=started_at, completedAt=completed_at,
            )
            return self.run_repository.append(run)
        except SourceError as error:
            code = error.code.value
            if code in {"SOURCE_NOT_FOUND", "SOURCE_VERSION_NOT_FOUND"}:
                raise CoverageServiceError(code, str(error), 404) from error
            raise CoverageServiceError("PROVENANCE_CONFLICT", str(error), 409) from error
        except (KeyError, LookupError) as error:
            raise CoverageServiceError(self._missing_code(error), "An immutable coverage input was not found.", 404) from error
        except CoverageServiceError:
            raise
        except ProviderTimeoutError as error:
            return self._persist_failed(request, run_id, correlation_id, digest, created_at, "PROVIDER_TIMEOUT", str(error), True)
        except ProviderOutputError as error:
            return self._persist_failed(request, run_id, correlation_id, digest, created_at, "MALFORMED_PROVIDER_OUTPUT", str(error), False)
        except (ExtractionIntegrityError, ValueError) as error:
            raise CoverageServiceError("PROVENANCE_CONFLICT", str(error), 409) from error
        except RuntimeError as error:
            if "idempotency" in str(error).casefold():
                raise CoverageServiceError("IDEMPOTENCY_KEY_CONFLICT", str(error), 409) from error
            return self._persist_failed(request, run_id, correlation_id, digest, created_at, "DEPENDENCY_UNAVAILABLE", str(error), True)
        except Exception as error:
            raise CoverageServiceError("INTERNAL_ERROR", "Coverage execution failed.", 500) from error

    def _validate_provenance(self, request: CoverageRunRequest, source: SourceDocument, extraction: SourceFactExtractionResult, claim_set: ClaimSetRecord) -> None:
        expected_context = (source.resident_test_id, f"{source.source_id}:v{source.source_version}")
        context = (request.resident_context.resident_test_id, request.resident_context.version)
        if context != expected_context or request.resident_context.source != "SPEC_001_SOURCE_DOCUMENT" or request.resident_context.trust_level != "AUTHORITATIVE_TRANSCRIPT":
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Resident context is not bound to the immutable transcript.", 409)
        if request.source_text_hash != source_text_hash(source.transcript_text):
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Source text hash does not match immutable source text.", 409)
        if request.normalization_policy != extraction.normalization_policy or request.normalization_policy != "NFC_CODEPOINTS":
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Normalization policy is inconsistent across inputs.", 409)
        if (extraction.source_id, extraction.source_version) != (request.source_id, request.source_version):
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Source-fact extraction is bound to another source version.", 409)
        if (claim_set.note_id, claim_set.note_revision) != (request.note_id, request.note_revision):
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Claim set is bound to another note revision.", 409)
        if (claim_set.source_id, claim_set.source_version) != (request.source_id, request.source_version):
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Claim set is bound to another source version.", 409)
        if claim_set.resident_test_id != source.resident_test_id:
            raise CoverageServiceError("PROVENANCE_CONFLICT", "Claim set resident does not match source resident.", 409)
        for claim in claim_set.claims:
            if claim.note_revision_id != f"{request.note_id}:r{request.note_revision}" or claim.resident_test_id != source.resident_test_id:
                raise CoverageServiceError("PROVENANCE_CONFLICT", "Claim belongs to another note revision or resident.", 409)

    @staticmethod
    def _counts(assessments, facts, unresolved) -> CoverageCounts:
        values = {status: sum(1 for item in assessments if item.source_fact_id is not None and item.status.value == status) for status in ("COVERED", "PARTIALLY_COVERED", "MISSING", "DISTORTED", "UNCERTAIN")}
        return CoverageCounts(
            extractedExpectedFacts=len(facts), coveredExpectedFacts=values["COVERED"], partiallyCoveredExpectedFacts=values["PARTIALLY_COVERED"],
            missingExpectedFacts=values["MISSING"], distortedExpectedFacts=values["DISTORTED"], uncertainExpectedFacts=values["UNCERTAIN"],
            unresolvedSourceItems=len(unresolved), unresolvedSourceItemsRequireReview=True,
            runtimeCompleteness=values["COVERED"] / len(facts) if facts else None, metricBasis="SYSTEM_EXTRACTED_EXPECTED_FACTS",
        )

    def _persist_failed(self, request, run_id, correlation_id, digest, created_at, code, message, retryable):
        completed = self._clock()
        run = CoverageRunFailed(
            coverageRunId=run_id, status=RunStatus.FAILED, sourceId=request.source_id, sourceVersion=request.source_version,
            residentContext=request.resident_context, sourceTextHash=request.source_text_hash, normalizationPolicy=request.normalization_policy,
            noteId=request.note_id, noteRevision=request.note_revision, sourceFactExtractionRunId=request.source_fact_extraction_run_id, claimSetId=request.claim_set_id,
            rulesetVersion=request.ruleset_version, coverageStatusPolicyVersion="COVERAGE_STATUS-v1", expectationPolicyVersion="COVERAGE_EXPECTATION-v1",
            datasetVersion=request.dataset_version, idempotencyKey=request.idempotency_key, correlationId=correlation_id, inputDigest=digest,
            providerVersion=getattr(self.matcher, "matcher_version", None), modelVersion=None, promptVersion=None,
            executionMetrics=ExecutionMetrics(latencyMilliseconds=0, retryCount=getattr(self.matcher, "last_retry_count", 0), inputTokens=None, outputTokens=None, inferenceCost=None, warningCount=0),
            createdAt=created_at, startedAt=created_at, completedAt=completed,
            failure=Failure(code=code, message=message or "Coverage provider failed.", retryable=retryable),
        )
        return self.run_repository.append(run)

    @staticmethod
    def _missing_code(error: Exception) -> str:
        text = str(error)
        if "source" in text.casefold():
            return "SOURCE_NOT_FOUND"
        if "claim" in text.casefold():
            return "CLAIM_SET_NOT_FOUND"
        return "SOURCE_FACT_EXTRACTION_NOT_FOUND"
