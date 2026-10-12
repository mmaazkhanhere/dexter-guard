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
        existing = next((item for item in self.review_service.repository.verifications.values() if item.idempotency_key == idempotency_key), None)
        if existing is not None:
            return existing
        runs: list[tuple[str, UpstreamRun | None]] = []
        try:
            extraction = ports.extract(note_id, expected_revision)
            runs.append(("CLAIM_EXTRACTION", extraction))
            runs.append(("EVIDENCE_VERIFICATION", ports.evidence(note_id, expected_revision, extraction.claim_set_id)))
            runs.append(("DETERMINISTIC_VALIDATION", ports.validation(note_id, expected_revision, extraction.claim_set_id)))
            runs.append(("SOURCE_COVERAGE", ports.coverage(note_id, expected_revision, extraction.claim_set_id)))
        except Exception:
            runs.append(("CLAIM_EXTRACTION", None))
        statuses = tuple(ComponentStatus(component=component, runId=run.run_id if run else None, status=("SUCCEEDED" if run and run.status == "SUCCEEDED" else "FAILED"), failureCode=None if run and run.status == "SUCCEEDED" else "DEPENDENCY_FAILURE") for component, run in runs)
        complete = len(runs) == 4
        provenance_ok = complete and all(run and (run.source_id, run.source_version, run.note_id, run.note_revision) == (note.source_id, note.source_version, note_id, expected_revision) for _, run in runs)
        all_success = complete and all(status.status == "SUCCEEDED" for status in statuses)
        status = "VALID" if all_success and provenance_ok else ("INVALID" if complete and not provenance_ok else "FAILED")
        verification = FullNoteVerification(fullVerificationId=f"full-{uuid4()}", noteId=note_id, noteRevision=expected_revision, source={"sourceId": note.source_id, "sourceVersion": note.source_version}, claimSetId=runs[0][1].claim_set_id if runs and runs[0][1] else "unavailable", evidenceRunId=next((r.run_id for c, r in runs if c == "EVIDENCE_VERIFICATION" and r), "unavailable"), deterministicValidationRunId=next((r.run_id for c, r in runs if c == "DETERMINISTIC_VALIDATION" and r), "unavailable"), coverageRunId=next((r.run_id for c, r in runs if c == "SOURCE_COVERAGE" and r), "unavailable"), componentStatuses=statuses, status=status, idempotencyKey=idempotency_key, requestDigest=digest, createdAt=datetime.now(timezone.utc), failureCode=None if status == "VALID" else ("PROVENANCE_CONFLICT" if status == "INVALID" else "DEPENDENCY_FAILURE"), failureMessage=None if status == "VALID" else "Full-note verification did not complete with exact current provenance.")
        self.review_service.persist_verification(verification)
        return verification
