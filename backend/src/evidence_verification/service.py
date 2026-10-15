"""Application service for immutable, fail-closed evidence verification."""

from __future__ import annotations

import hashlib
import inspect
import re
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from pydantic import ValidationError

from .contracts import (
    ANNOTATION_POLICY_VERSION,
    EVIDENCE_STATUS_POLICY_VERSION,
    EvidenceFinding,
    EvidenceRole,
    EvidenceStatus,
    VerificationFailure,
    VerificationRun,
    VerificationRunFailed,
    VerificationRunRequest,
    VerificationRunSucceeded,
)
from .provider import (
    MalformedVerifierOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    StructuredVerifierAdapter,
    VerifierCandidateFinding,
    VerifierResponse,
    provider_metadata,
)
from .repository import InMemoryVerificationRepository, VerificationRunRepository
from .observability import VerificationMetrics
from .discovery import discover_candidate_evidence
from .validation import (
    IdempotencyKeyConflictError,
    VerificationIntegrityError,
    canonical_request_digest,
    validate_successful_run,
)


class VerificationServiceError(RuntimeError):
    """A safe, structured domain failure before a run can be returned."""


class VerificationService:
    """Coordinates source, note, claim, verifier, and persistence adapters.

    All dependencies are injected.  The service never accepts claim assertion
    text from the request and never mutates any upstream record.
    """

    def __init__(
        self,
        source_repository: object | None = None,
        claim_repository: object | None = None,
        verifier: object | None = None,
        *,
        source_service: object | None = None,
        note_repository: object | None = None,
        claim_resolver: Callable[[str], object] | None = None,
        provider: object | None = None,
        repository: VerificationRunRepository | None = None,
        run_repository: VerificationRunRepository | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        correlation_factory: Callable[[], str] | None = None,
        provider_timeout_seconds: float = 30.0,
        max_provider_attempts: int = 2,
        logger: object | None = None,
        metrics: VerificationMetrics | None = None,
    ) -> None:
        if provider_timeout_seconds <= 0:
            raise ValueError("provider_timeout_seconds must be positive")
        if verifier is None:
            verifier = provider
        if verifier is None:
            raise ValueError("verifier or provider must be configured")
        self.source_repository = source_repository
        self.source_service = source_service
        self.note_repository = note_repository
        self.claim_repository = claim_repository
        self.claim_resolver = claim_resolver
        self.verifier = verifier if isinstance(verifier, StructuredVerifierAdapter) else StructuredVerifierAdapter(verifier, max_attempts=max_provider_attempts)
        self.repository = repository or run_repository or InMemoryVerificationRepository()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._correlation_factory = correlation_factory or (lambda: str(uuid4()))
        self.provider_timeout_seconds = provider_timeout_seconds
        self.logger = logger
        self.metrics = metrics or VerificationMetrics()

    def verify(self, payload: VerificationRunRequest | Mapping[str, object]) -> VerificationRun:
        request = payload if isinstance(payload, VerificationRunRequest) else VerificationRunRequest.model_validate(payload)
        run_id = f"verification-{self._id_factory()}"
        created_at = self._clock()
        digest = canonical_request_digest(request)

        reservation = self.repository.reserve_or_replay(request, run_id)
        if reservation.existing is not None:
            return reservation.existing

        correlation_id = self._correlation_factory()
        trace_id = self._correlation_factory()

        metadata = provider_metadata(getattr(self.verifier, "provider", self.verifier))
        started_at = self._clock()
        try:
            source = self._resolve_source(request)
            claims = self._resolve_claims(request, source)
            self._validate_note(request, source)
        except Exception as error:
            self.metrics.increment("validation_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_VALIDATION",
                code=self._safe_validation_code(error),
                reason=self._safe_reason(error, "Immutable verification inputs could not be resolved."),
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )

        try:
            candidate_evidence = discover_candidate_evidence(claims, source.transcript_text)
            response = self._invoke_verifier(
                candidate_evidence,
                source.transcript_text,
                run_id,
                source_id=request.source_id,
                source_version=request.source_version,
            )
        except (ProviderTimeoutError, FutureTimeoutError, TimeoutError):
            self.metrics.increment("provider_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_VERIFIER",
                code="PROVIDER_TIMEOUT",
                reason="The evidence-verifier provider exceeded its configured timeout.",
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )
        except ProviderUnavailableError:
            self.metrics.increment("provider_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_VERIFIER",
                code="PROVIDER_UNAVAILABLE",
                reason="The evidence-verifier provider was unavailable.",
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )
        except MalformedVerifierOutputError:
            self.metrics.increment("provider_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_VERIFIER",
                code="MALFORMED_VERIFIER_OUTPUT",
                reason="The evidence-verifier response failed its structured contract.",
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )

        try:
            findings = self._normalize_findings(response, request, source.transcript_text, claims)
            completed_at = self._clock()
            run = VerificationRunSucceeded(
                verificationRunId=run_id,
                sourceId=request.source_id,
                sourceVersion=request.source_version,
                noteId=request.note_id,
                noteRevision=request.note_revision,
                claimSetId=request.claim_set_id,
                idempotencyKey=request.idempotency_key,
                inputDigest=digest,
                evidenceStatusPolicyVersion=EVIDENCE_STATUS_POLICY_VERSION,
                annotationPolicyVersion=ANNOTATION_POLICY_VERSION,
                modelId=metadata["model_id"] or "configured-verifier",
                modelVersion=metadata["model_version"] or "unknown",
                promptVersion=metadata["prompt_version"] or "verification-v1",
                promptHash=metadata["prompt_hash"] or "sha256:verification-v1",
                correlationId=correlation_id,
                executionTraceId=trace_id,
                createdAt=created_at,
                startedAt=started_at,
                completedAt=completed_at,
                status="SUCCEEDED",
                findings=findings,
            )
            validate_successful_run(request, run, source.transcript_text)
        except MalformedVerifierOutputError:
            self.metrics.increment("provider_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_VERIFIER",
                code="MALFORMED_VERIFIER_OUTPUT",
                reason="The evidence-verifier response did not cover the requested claims.",
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )
        except VerificationIntegrityError as error:
            self.metrics.increment("evidence_integrity_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_EVIDENCE_INTEGRITY",
                code="INVALID_EVIDENCE",
                reason=self._safe_reason(error, "Verifier evidence did not match the immutable source."),
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )
        except (ValidationError, ValueError, TypeError) as error:
            self.metrics.increment("evidence_integrity_failures")
            return self._persist_failure(
                request,
                run_id=run_id,
                digest=digest,
                status="FAILED_EVIDENCE_INTEGRITY",
                code="INVALID_EVIDENCE",
                reason=self._safe_reason(error, "Verifier evidence did not satisfy the evidence contract."),
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=created_at,
                started_at=started_at,
            )

        return self._persist_success(run, request, metadata, correlation_id, trace_id)

    verify_claims = verify
    run = verify

    def _resolve_source(self, request: VerificationRunRequest) -> object:
        getter = getattr(self.source_repository, "get", None) if self.source_repository is not None else None
        if getter is None and self.source_service is not None:
            getter = getattr(self.source_service, "get_source_version", None)
        if getter is None:
            raise VerificationServiceError("SOURCE_NOT_FOUND")
        try:
            source = getter(request.source_id, request.source_version)
        except Exception as error:
            raise VerificationServiceError("SOURCE_NOT_FOUND") from error
        if getattr(source, "source_id", None) != request.source_id or getattr(source, "source_version", None) != request.source_version:
            raise VerificationServiceError("SOURCE_VERSION_MISMATCH")
        if not getattr(source, "transcript_text", None):
            raise VerificationServiceError("SOURCE_NOT_FOUND")
        if getattr(source, "resident_test_id", None) in {None, "UNKNOWN"}:
            raise VerificationServiceError("RESIDENT_MISMATCH")
        for claim in request.claims:
            if claim.resident_test_id != source.resident_test_id:
                raise VerificationServiceError("RESIDENT_MISMATCH")
        return source

    def _validate_note(self, request: VerificationRunRequest, source: object) -> None:
        if self.note_repository is None:
            return
        getter = getattr(self.note_repository, "get", None)
        if getter is None:
            raise VerificationServiceError("NOTE_NOT_FOUND")
        try:
            note = getter(request.note_id, request.note_revision)
        except Exception as error:
            raise VerificationServiceError("NOTE_NOT_FOUND") from error
        if getattr(note, "source_id", None) != request.source_id or getattr(note, "source_version", None) != request.source_version:
            raise VerificationServiceError("NOTE_SOURCE_MISMATCH")
        source_hash = getattr(note, "source_text_hash", None)
        if source_hash and source_hash != hashlib.sha256(source.transcript_text.encode("utf-8")).hexdigest():
            raise VerificationServiceError("SOURCE_INTEGRITY_MISMATCH")

    def _resolve_claims(self, request: VerificationRunRequest, source: object) -> tuple[object, ...]:
        result: object | None = None
        if self.claim_resolver is not None:
            result = self.claim_resolver(request.claim_set_id)
        elif self.claim_repository is not None:
            for method_name in ("get_by_extraction_run_id", "get_result", "get"):
                method = getattr(self.claim_repository, method_name, None)
                if method is None:
                    continue
                try:
                    result = method(request.claim_set_id)
                except TypeError:
                    continue
                except Exception:
                    result = None
                if result is not None:
                    break
        if result is None:
            raise VerificationServiceError("UNKNOWN_CLAIM_SET")
        if getattr(result, "status", None) is not None and str(getattr(result, "status")) not in {"SUCCEEDED", "ExtractionStatus.SUCCEEDED"}:
            raise VerificationServiceError("CLAIM_SET_NOT_SUCCESSFUL")
        if getattr(result, "extraction_run_id", request.claim_set_id) != request.claim_set_id:
            raise VerificationServiceError("CLAIM_SET_MISMATCH")
        available = {getattr(claim, "id", None): claim for claim in getattr(result, "claims", ())}
        resolved: list[object] = []
        expected_note_revision = f"{request.note_id}:r{request.note_revision}"
        for requested in request.claims:
            claim = available.get(requested.claim_id)
            if claim is None:
                raise VerificationServiceError("UNKNOWN_CLAIM")
            if getattr(claim, "note_revision_id", None) != expected_note_revision:
                raise VerificationServiceError("CLAIM_REVISION_MISMATCH")
            if getattr(claim, "resident_test_id", None) != source.resident_test_id:
                raise VerificationServiceError("RESIDENT_MISMATCH")
            resolved.append(claim)
        return tuple(resolved)

    def _invoke_verifier(
        self,
        claims: Sequence[object],
        source_text: str,
        run_id: str,
        *,
        source_id: str | None = None,
        source_version: int | None = None,
    ) -> VerifierResponse:
        self.metrics.increment("provider_attempts")
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.verifier.verify,
            claims=claims,
            source_text=source_text,
            run_id=run_id,
            source_id=source_id,
            source_version=source_version,
        )
        timed_out = False
        try:
            response = future.result(timeout=self.provider_timeout_seconds)
            self.metrics.increment_by("provider_attempts", getattr(self.verifier, "last_retry_count", 0))
            self.metrics.record_provider_usage(
                input_tokens=getattr(self.verifier, "last_input_tokens", None),
                output_tokens=getattr(self.verifier, "last_output_tokens", None),
                inference_cost=getattr(self.verifier, "last_inference_cost", None),
            )
            return response
        except FutureTimeoutError:
            timed_out = True
            future.cancel()
            raise ProviderTimeoutError("provider timeout")
        finally:
            executor.shutdown(wait=not timed_out, cancel_futures=True)

    def _normalize_findings(
        self,
        response: VerifierResponse,
        request: VerificationRunRequest,
        source_text: str,
        resolved_claims: Sequence[object] = (),
    ) -> tuple[EvidenceFinding, ...]:
        expected_ids = {claim.claim_id for claim in request.claims}
        candidates = list(response.findings)
        ids = [candidate.claim_id for candidate in candidates]
        if len(ids) != len(set(ids)) or set(ids) != expected_ids:
            self.metrics.increment("coverage_failures")
            raise MalformedVerifierOutputError("Verifier findings must cover exactly the submitted claim IDs.")
        normalized: list[EvidenceFinding] = []
        claims_by_id = {claim.claim_id: claim for claim in request.claims}
        claims_by_id.update({str(getattr(claim, "id")): claim for claim in resolved_claims})
        for candidate in candidates:
            spans = tuple(candidate.source_spans)
            quotes = self._quotes_for(candidate, spans, source_text)
            status = candidate.status
            discrepancies = candidate.discrepancies
            explanation = candidate.explanation
            claim_text = str(getattr(claims_by_id[candidate.claim_id], "claim_text", ""))
            if status is EvidenceStatus.SUPPORTED and self._has_compound_assertion(claim_text):
                status = EvidenceStatus.UNCERTAIN
                discrepancies = tuple(dict.fromkeys((*discrepancies, "OTHER")))
                explanation = (
                    "The verifier marked a compound claim as supported without separate subclaim evidence; "
                    "the result is conservatively uncertain."
                )
            finding = EvidenceFinding(
                claimId=candidate.claim_id,
                status=status,
                explanation=explanation,
                sourceSpans=spans,
                evidenceQuotes=quotes,
                discrepancies=discrepancies,
                policyVersion=ANNOTATION_POLICY_VERSION,
                verifierFinding={"status": candidate.status, "explanation": candidate.explanation},
                deterministicRuleFindings=[
                    {"code": "COMPOUND_ASSERTION_GUARD", "outcome": "WARNING"}
                    if status is not candidate.status
                    else {"code": "CONTRACT", "outcome": "PASS"}
                ],
            )
            normalized.append(finding)
        return tuple(normalized)

    @staticmethod
    def _has_compound_assertion(claim_text: str) -> bool:
        """Detect common German assertion boundaries for conservative fallback."""

        return bool(re.search(r"\s+(?:und|aber|doch|sowie)\s+|,\s+(?=[A-Za-zÄÖÜäöüß])", claim_text, re.IGNORECASE))

    def _quotes_for(self, candidate: VerifierCandidateFinding, spans: tuple[object, ...], source_text: str) -> tuple[dict[str, object], ...]:
        supplied = list(candidate.evidence_quotes)
        if supplied:
            if len(supplied) != len(spans):
                self.metrics.increment("span_integrity_failures")
                raise VerificationIntegrityError("evidence quotations must pair one-to-one with source spans")
            by_key = {(span.source_id, span.source_version, span.start, span.end): span for span in spans}
            result: list[dict[str, object]] = []
            for quote in supplied:
                key = (quote.span.source_id, quote.span.source_version, quote.span.start, quote.span.end)
                if key not in by_key or quote.text != source_text[quote.span.start : quote.span.end]:
                    self.metrics.increment("span_integrity_failures")
                    raise VerificationIntegrityError("evidence quotation must equal its exact immutable-source substring")
                result.append({"span": quote.span, "text": quote.text, "evidenceRole": quote.evidence_role})
            return tuple(result)
        if candidate.status is EvidenceStatus.UNSUPPORTED:
            role = EvidenceRole.CONTEXT_NON_SUPPORTING
        elif candidate.status is EvidenceStatus.CONTRADICTED:
            role = EvidenceRole.CONFLICTING
        else:
            role = EvidenceRole.SUPPORTING
        return tuple({"span": span, "text": source_text[span.start : span.end], "evidenceRole": role} for span in spans)

    def _persist_success(
        self,
        run: VerificationRunSucceeded,
        request: VerificationRunRequest,
        metadata: dict[str, str | None],
        correlation_id: str,
        trace_id: str,
    ) -> VerificationRun:
        try:
            persisted = self.repository.save(run)
            self.metrics.increment("successful_runs")
            self.metrics.record_terminal(
                status="SUCCEEDED",
                latency_ms=(run.completed_at - run.created_at).total_seconds() * 1000,
                metadata={
                    "model_version": run.model_version,
                    "prompt_version": run.prompt_version,
                    "annotation_policy_version": run.annotation_policy_version,
                },
            )
            self._log(
                "verification_completed",
                status="SUCCEEDED",
                run_id=run.verification_run_id,
                model_id=run.model_id,
                model_version=run.model_version,
                prompt_version=run.prompt_version,
                annotation_policy_version=run.annotation_policy_version,
                evidence_status_policy_version=run.evidence_status_policy_version,
            )
            return persisted
        except Exception:
            self.metrics.increment("persistence_failures")
            failure = self._failure_run(
                request,
                run_id=run.verification_run_id,
                digest=run.input_digest,
                status="FAILED_PERSISTENCE",
                code="PERSISTENCE_FAILURE",
                reason="The verification result could not be durably persisted.",
                metadata=metadata,
                correlation_id=correlation_id,
                trace_id=trace_id,
                created_at=run.created_at,
                started_at=run.started_at,
            )
            try:
                return self.repository.save(failure)
            except Exception:
                return failure

    def _persist_failure(self, request: VerificationRunRequest, **kwargs: object) -> VerificationRun:
        failure = self._failure_run(request, **kwargs)
        self.metrics.record_terminal(
            status=failure.status,
            latency_ms=(failure.completed_at - failure.created_at).total_seconds() * 1000,
            metadata={
                "model_version": failure.model_version,
                "prompt_version": failure.prompt_version,
                "annotation_policy_version": failure.annotation_policy_version,
            },
            failure_code=failure.failure.code,
        )
        try:
            persisted = self.repository.save(failure)
        except Exception:
            return failure
        self._log("verification_completed", status=failure.status, run_id=failure.verification_run_id)
        return persisted

    @staticmethod
    def _failure_run(
        request: VerificationRunRequest,
        *,
        run_id: str,
        digest: str,
        status: str,
        code: str,
        reason: str,
        metadata: dict[str, str | None],
        correlation_id: str,
        trace_id: str,
        created_at: datetime,
        started_at: datetime,
    ) -> VerificationRunFailed:
        completed_at = started_at if started_at >= created_at else created_at
        return VerificationRunFailed(
            verificationRunId=run_id,
            sourceId=request.source_id,
            sourceVersion=request.source_version,
            noteId=request.note_id,
            noteRevision=request.note_revision,
            claimSetId=request.claim_set_id,
            idempotencyKey=request.idempotency_key,
            inputDigest=digest,
            evidenceStatusPolicyVersion=EVIDENCE_STATUS_POLICY_VERSION,
            annotationPolicyVersion=ANNOTATION_POLICY_VERSION,
            modelId=metadata.get("model_id"),
            modelVersion=metadata.get("model_version"),
            promptVersion=metadata.get("prompt_version"),
            promptHash=metadata.get("prompt_hash"),
            correlationId=correlation_id,
            executionTraceId=trace_id,
            createdAt=created_at,
            startedAt=started_at,
            completedAt=completed_at,
            status=status,
            failure=VerificationFailure(code=code, reason=reason),
        )

    @staticmethod
    def _safe_validation_code(error: Exception) -> str:
        return str(error) if isinstance(error, VerificationServiceError) else "PROVENANCE_VALIDATION_FAILED"

    @staticmethod
    def _safe_reason(error: Exception, default: str) -> str:
        if isinstance(error, VerificationServiceError) and str(error):
            return "Immutable verification input failed: " + str(error)
        if isinstance(error, VerificationIntegrityError) and str(error):
            return str(error)
        return default

    def _log(self, event: str, **fields: object) -> None:
        if self.logger is not None and hasattr(self.logger, "event"):
            self.logger.event(event, **fields)

