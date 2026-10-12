from __future__ import annotations

import hashlib
import json
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
    def __init__(self, review_service) -> None:
        self.review_service = review_service

    def verify(self, note_id: str, *, expected_revision: int, ports, reviewer_label: str, idempotency_key: str) -> FullNoteVerification:
        note = self.review_service.get_note(note_id)
        if note.revision != expected_revision:
            raise RuntimeError("STALE_REVISION")
        digest = hashlib.sha256(json.dumps({"note": note_id, "revision": expected_revision, "key": idempotency_key}, sort_keys=True).encode()).hexdigest()
        self.review_service._bind_idempotency("full-verification", idempotency_key, digest)
        existing = next((item for item in self.review_service.repository.verifications.values() if item.idempotency_key == idempotency_key), None)
        if existing is not None:
            return existing
        runs: list[tuple[str, UpstreamRun | None]] = []
        extraction = None
        for component, operation in (("CLAIM_EXTRACTION", lambda: ports.extract(note_id, expected_revision)),):
            try:
                extraction = operation()
            except Exception:
                extraction = None
            runs.append((component, extraction))
        claim_set_id = extraction.claim_set_id if extraction else "unavailable"
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
        statuses = tuple(ComponentStatus(component=component, runId=run.run_id if run else None, status=("SUCCEEDED" if run and run.status == "SUCCEEDED" else "FAILED"), failureCode=None if run and run.status == "SUCCEEDED" else "DEPENDENCY_FAILURE") for component, run in runs)
        complete = len(runs) == 4 and all(run is not None for _, run in runs)
        provenance_ok = complete and all(run and (run.source_id, run.source_version, run.note_id, run.note_revision, run.claim_set_id) == (note.source_id, note.source_version, note_id, expected_revision, claim_set_id) for _, run in runs)
        all_success = complete and all(status.status == "SUCCEEDED" for status in statuses)
        unresolved_source_items = next((getattr(r, "unresolved_source_items", 0) for c, r in runs if c == "SOURCE_COVERAGE" and r), 0)
        status = "VALID" if all_success and provenance_ok and unresolved_source_items == 0 else ("INVALID" if complete and (not provenance_ok or unresolved_source_items > 0) else "FAILED")
        verification = FullNoteVerification(fullVerificationId=f"full-{uuid4()}", noteId=note_id, noteRevision=expected_revision, source={"sourceId": note.source_id, "sourceVersion": note.source_version}, claimSetId=claim_set_id, evidenceRunId=next((r.run_id for c, r in runs if c == "EVIDENCE_VERIFICATION" and r), "unavailable"), deterministicValidationRunId=next((r.run_id for c, r in runs if c == "DETERMINISTIC_VALIDATION" and r), "unavailable"), coverageRunId=next((r.run_id for c, r in runs if c == "SOURCE_COVERAGE" and r), "unavailable"), coverageUnresolvedSourceItems=unresolved_source_items, componentStatuses=statuses, status=status, idempotencyKey=idempotency_key, requestDigest=digest, createdAt=datetime.now(timezone.utc), failureCode=None if status == "VALID" else ("PROVENANCE_CONFLICT" if complete and not provenance_ok else ("UNRESOLVED_SOURCE_ITEM" if unresolved_source_items else "DEPENDENCY_FAILURE")), failureMessage=None if status == "VALID" else "Full-note verification did not complete with exact current provenance.")
        self.review_service.persist_verification(verification)
        return verification
