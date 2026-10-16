from __future__ import annotations

import hashlib
import json
from time import perf_counter
from datetime import datetime, timezone
from uuid import uuid4

from .contracts import ComponentStatus, FullNoteVerification
from .ports import UpstreamRun


class ClaimFeedback:
    def __init__(self, *, note_id: str, revision: int, claim_id: str, run_id: str, status: str) -> None:
        self.review_verification_id = f"claim-feedback-{uuid4()}"
        self.note_id, self.note_revision, self.claim_id = note_id, revision, claim_id
        self.upstream_verification_run_id, self.status, self.approval_eligible = run_id, status, False


class FullNoteVerificationService:
    def __init__(self, review_service, *, metrics=None, logger=None) -> None:
        self.review_service = review_service
        self.metrics = metrics
        self.logger = logger

    def verify(self, note_id: str, *, expected_revision: int, ports, reviewer_label: str, idempotency_key: str) -> FullNoteVerification:
        started = perf_counter()
        note = self.review_service.get_note(note_id)
        if note.revision != expected_revision:
            raise RuntimeError("STALE_REVISION")
        digest = hashlib.sha256(json.dumps({"note": note_id, "revision": expected_revision, "key": idempotency_key, "reviewerLabel": reviewer_label}, sort_keys=True).encode()).hexdigest()
        self.review_service._bind_idempotency("full-verification", idempotency_key, digest)
        existing = next((item for item in self.review_service.repository.verifications.values() if item.idempotency_key == idempotency_key), None)
        if existing is not None:
            if self.metrics:
                self.metrics.increment("retry_replays")
            return existing
        runs: list[tuple[str, UpstreamRun | None]] = []
        extraction = None
        for component, operation in (("CLAIM_EXTRACTION", lambda: ports.extract(note_id, expected_revision)),):
            try:
                extraction = operation()
            except Exception:
                extraction = None
            runs.append((component, extraction))
        claim_set_id = getattr(extraction, "claim_set_id", None) if extraction else "unavailable"
        if not claim_set_id:
            claim_set_id = "unavailable"
        for component, operation in (
            ("EVIDENCE_VERIFICATION", lambda: ports.evidence(note_id, expected_revision, claim_set_id)),
            ("DETERMINISTIC_VALIDATION", lambda: ports.validation(note_id, expected_revision, claim_set_id)),
            ("SOURCE_COVERAGE", lambda: ports.coverage(note_id, expected_revision, claim_set_id)),
        ):
            try:
                run = operation()
            except Exception:
                run = None
            runs.append((component, run))
        def component_status(run):
            if run is None:
                return "UNAVAILABLE", "DEPENDENCY_UNAVAILABLE"
            upstream_status = getattr(run, "status", None)
            if upstream_status == "SUCCEEDED":
                return "SUCCEEDED", None
            if upstream_status == "INVALID":
                return "INVALID", "MALFORMED_UPSTREAM_RESULT"
            if upstream_status is None:
                return "INVALID", "MALFORMED_UPSTREAM_RESULT"
            return "FAILED", getattr(run, "failure_code", None) or "UPSTREAM_FAILURE"

        statuses = tuple(ComponentStatus(component=component, runId=getattr(run, "run_id", None), status=component_status(run)[0], failureCode=component_status(run)[1]) for component, run in runs)
        complete = len(runs) == 4 and all(run is not None for _, run in runs)
        provenance_ok = complete and all(run and (getattr(run, "source_id", None), getattr(run, "source_version", None), getattr(run, "note_id", None), getattr(run, "note_revision", None), getattr(run, "claim_set_id", None)) == (note.source_id, note.source_version, note_id, expected_revision, claim_set_id) for _, run in runs)
        all_success = complete and all(status.status == "SUCCEEDED" for status in statuses)
        unresolved_source_items = next((getattr(r, "unresolved_source_items", 0) for c, r in runs if c == "SOURCE_COVERAGE" and r), 0)
        empty_claim_set = extraction is not None and getattr(extraction, "claim_count", None) == 0
        status = "VALID" if all_success and provenance_ok and claim_set_id != "unavailable" and not empty_claim_set and unresolved_source_items == 0 else ("INVALID" if complete and (not provenance_ok or unresolved_source_items > 0 or claim_set_id == "unavailable" or empty_claim_set) else "FAILED")
        failure_code = None if status == "VALID" else ("PROVENANCE_CONFLICT" if complete and not provenance_ok else ("UNRESOLVED_SOURCE_ITEM" if unresolved_source_items else ("EMPTY_CLAIM_SET_REQUIRES_REVIEW" if claim_set_id == "unavailable" or empty_claim_set else next((item.failure_code for item in statuses if item.failure_code), "DEPENDENCY_FAILURE"))))
        failure_message = None if status == "VALID" else self._safe_failure_message(failure_code, runs)
        now = self.review_service.clock()
        verification = FullNoteVerification(fullVerificationId=f"full-{uuid4()}", noteId=note_id, noteRevision=expected_revision, source={"sourceId": note.source_id, "sourceVersion": note.source_version}, claimSetId=claim_set_id, evidenceRunId=next((r.run_id for c, r in runs if c == "EVIDENCE_VERIFICATION" and r), "unavailable"), deterministicValidationRunId=next((r.run_id for c, r in runs if c == "DETERMINISTIC_VALIDATION" and r), "unavailable"), coverageRunId=next((r.run_id for c, r in runs if c == "SOURCE_COVERAGE" and r), "unavailable"), coverageUnresolvedSourceItems=unresolved_source_items, componentStatuses=statuses, status=status, idempotencyKey=idempotency_key, requestDigest=digest, correlationId=f"full-{note_id}-{expected_revision}", failureCode=failure_code, failureMessage=failure_message, createdAt=now, completedAt=now)
        self.review_service.persist_verification(verification)
        if self.metrics:
            self.metrics.record_verification(status=verification.status, latency_ms=(perf_counter() - started) * 1000.0, failure_code=verification.failure_code)
        if self.logger:
            self.logger.event("FULL_VERIFICATION_COMPLETED", noteId=note_id, noteRevision=expected_revision, status=verification.status, failureCode=verification.failure_code, idempotencyKey=idempotency_key)
        return verification

    @staticmethod
    def _safe_failure_message(failure_code: str | None, runs: list[tuple[str, UpstreamRun | None]]) -> str:
        """Return a caregiver-safe action message, never an upstream exception."""
        evidence_run = next((run for component, run in runs if component == "EVIDENCE_VERIFICATION"), None)
        if failure_code == "PROVIDER_TIMEOUT":
            return "Evidence verification took too long. The note was not approved; try verification again."
        if failure_code == "PROVIDER_UNAVAILABLE":
            return "Evidence verification is temporarily unavailable. The note was not approved; try verification again."
        if failure_code == "MALFORMED_VERIFIER_OUTPUT":
            return "Evidence verification returned an invalid response. The note was not approved; try verification again."
        if evidence_run is not None and getattr(evidence_run, "failure_reason", None):
            return "Evidence verification did not complete. The note was not approved; try verification again."
        return "Full-note verification did not complete. The note was not approved; try verification again."
