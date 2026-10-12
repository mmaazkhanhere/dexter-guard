from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .approval import ApprovalEligibilityPolicy, ReviewServiceError
from .contracts import AuditEvent, ClaimReverificationResponse, FullNoteVerification, NoteDisposition, ReviewDecision, ReviewFinding, SuggestedCorrection
from .repository import InMemoryReviewRepository, ReviewRepositoryError


@dataclass(frozen=True)
class NoteRecord:
    note_id: str
    revision: int
    source_id: str
    source_version: int
    content: str


class ReviewService:
    def __init__(self, repository: InMemoryReviewRepository | None = None, *, clock=None, id_factory=None) -> None:
        self.repository = repository or InMemoryReviewRepository()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.id_factory = id_factory or (lambda: str(uuid4()))

    def _event(self, note_id: str, revision: int, actor: str, event_type: str, target_type: str, target_id: str, references=(), rationale=None) -> AuditEvent:
        payload = json.dumps({"eventType": event_type, "targetId": target_id, "references": list(references)}, sort_keys=True)
        return AuditEvent(eventId=f"event-{self.id_factory()}", sequence=len(self.repository.audit(note_id)) + 1, occurredAt=self.clock(), actorLabel=actor, eventType=event_type, noteId=note_id, noteRevision=revision, targetType=target_type, targetId=target_id, references=tuple(references), payloadDigest=hashlib.sha256(payload.encode()).hexdigest(), rationale=rationale)

    def seed_note(self, note_id: str, source_id: str, source_version: int, content: str) -> NoteRecord:
        note = NoteRecord(note_id, 1, source_id, source_version, content)
        self.repository.notes[(note_id, 1)] = note
        self.repository.latest[note_id] = 1
        self.repository.persist_note(note)
        self.repository.append_event(self._event(note_id, 1, "SYSTEM", "NOTE_CREATED", "NOTE_REVISION", f"{note_id}:r1"))
        return note

    def get_note(self, note_id: str, revision: int | None = None) -> NoteRecord:
        selected = revision or self.repository.latest.get(note_id)
        note = self.repository.notes.get((note_id, selected))
        if note is None:
            raise ReviewServiceError("NOTE_NOT_FOUND")
        return note

    def save_revision(self, note_id: str, *, expected_revision: int, content: str, reviewer_label: str, idempotency_key: str | None = None) -> NoteRecord:
        with self.repository._lock:
            latest = self.get_note(note_id)
            if any(disposition.note_id == note_id for disposition in self.repository.dispositions):
                raise ReviewServiceError("FINAL_DISPOSITION_IMMUTABLE")
            if latest.revision != expected_revision:
                raise ReviewServiceError("STALE_REVISION")
            if idempotency_key:
                self._bind_idempotency("save-revision", idempotency_key, json.dumps({"noteId": note_id, "revision": expected_revision, "content": content}, sort_keys=True))
            successor = NoteRecord(note_id, latest.revision + 1, latest.source_id, latest.source_version, content)
            self.repository.notes[(note_id, successor.revision)] = successor
            self.repository.latest[note_id] = successor.revision
            self.repository.persist_note(successor)
            self.repository.append_event(self._event(note_id, successor.revision, reviewer_label, "NOTE_REVISION_CREATED", "NOTE_REVISION", f"{note_id}:r{successor.revision}", (f"{note_id}:r{latest.revision}",)))
            return successor

    def add_finding(self, finding: ReviewFinding) -> None:
        note = self.get_note(finding.note_id, finding.note_revision)
        if (note.source_id, note.source_version) != (finding.source_id, finding.source_version):
            raise ReviewServiceError("PROVENANCE_CONFLICT")
        self.repository.findings[finding.review_finding_id] = finding
        self.repository.persist_finding(finding)

    def add_suggestion(self, suggestion: SuggestedCorrection) -> None:
        if suggestion.note_id not in self.repository.latest:
            raise ReviewServiceError("NOTE_NOT_FOUND")
        if suggestion.support_status == "USABLE" and not suggestion.support_spans:
            raise ReviewServiceError("SUGGESTION_NOT_USABLE")
        self.repository.suggestions[suggestion.suggestion_id] = suggestion
        self.repository.persist_suggestion(suggestion)

    def accept_suggestion(self, note_id: str, *, suggestion_id: str, expected_revision: int, reviewer_label: str) -> NoteRecord:
        suggestion = self.repository.suggestions.get(suggestion_id)
        if suggestion is None or suggestion.note_id != note_id or suggestion.support_status != "USABLE":
            raise ReviewServiceError("SUGGESTION_NOT_USABLE")
        note = self.get_note(note_id)
        if note.revision != expected_revision or suggestion.base_revision != expected_revision:
            raise ReviewServiceError("STALE_REVISION")
        start = suggestion.target_note_span.start_code_point
        end = suggestion.target_note_span.end_code_point_exclusive
        if note.content[start:end] != suggestion.target_note_span.text:
            raise ReviewServiceError("SUGGESTION_TARGET_MISMATCH")
        return self.save_revision(note_id, expected_revision=expected_revision, content=note.content[:start] + suggestion.replacement + note.content[end:], reviewer_label=reviewer_label)

    def record_decision(self, note_id: str, finding_id: str, *, expected_revision: int, kind: str, reviewer_label: str, rationale: str | None = None, suggestion_id: str | None = None, idempotency_key: str | None = None) -> ReviewDecision:
        if idempotency_key:
            self._bind_idempotency("finding-decision", idempotency_key, json.dumps({"noteId": note_id, "findingId": finding_id, "revision": expected_revision, "kind": kind, "suggestionId": suggestion_id, "rationale": rationale}, sort_keys=True))
        finding = self.repository.findings.get(finding_id)
        if finding is None or finding.note_id != note_id:
            raise ReviewServiceError("FINDING_NOT_FOUND")
        if self.get_note(note_id).revision != expected_revision:
            raise ReviewServiceError("STALE_REVISION")
        successor_revision = None
        if kind == "SUGGESTION_ACCEPTED":
            if not suggestion_id:
                raise ReviewServiceError("SUGGESTION_NOT_USABLE")
            successor = self.accept_suggestion(note_id, suggestion_id=suggestion_id, expected_revision=expected_revision, reviewer_label=reviewer_label)
            successor_revision = successor.revision
            outcome = "RESOLVED"
        elif kind == "SUGGESTION_REJECTED":
            if not suggestion_id:
                raise ReviewServiceError("SUGGESTION_NOT_FOUND")
            outcome = "NO_STATE_CHANGE"
        else:
            outcome = "NO_STATE_CHANGE" if kind in {"ACKNOWLEDGED", "DISPUTED"} or finding.severity == "CRITICAL" else "ADJUDICATED"
        decision = ReviewDecision(reviewDecisionId=f"decision-{self.id_factory()}", findingId=finding_id, noteId=note_id, noteRevision=expected_revision, kind=kind, outcome=outcome, reviewerLabel=reviewer_label, rationale=rationale, successorRevision=successor_revision, suggestionId=suggestion_id, idempotencyKey=idempotency_key, recordedAt=self.clock())
        self.repository.decisions.append(decision)
        self.repository.persist_decision(decision)
        self.repository.append_event(self._event(note_id, expected_revision, reviewer_label, "FINDING_DECISION_RECORDED", "REVIEW_DECISION", decision.review_decision_id, (finding_id,), rationale))
        return decision

    def persist_verification(self, verification: FullNoteVerification) -> FullNoteVerification:
        note = self.get_note(verification.note_id, verification.note_revision)
        if (note.source_id, note.source_version) != (verification.source.source_id, verification.source.source_version):
            raise ReviewServiceError("PROVENANCE_CONFLICT")
        current = self.repository.verifications.get(verification.full_verification_id)
        if current is not None and current != verification:
            raise ReviewServiceError("IMMUTABLE_RECORD_CONFLICT")
        self.repository.verifications[verification.full_verification_id] = verification
        self.repository.persist_verification(verification)
        return verification

    def approve(self, note_id: str, *, expected_revision: int, full_verification: FullNoteVerification, reviewer_label: str, rationale: str | None = None, idempotency_key: str | None = None) -> NoteDisposition:
        with self.repository._lock:
            latest = self.get_note(note_id)
            if latest.revision != expected_revision:
                raise ReviewServiceError("STALE_REVISION")
            persisted = self.repository.verifications.get(full_verification.full_verification_id)
            if persisted != full_verification:
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
            ApprovalEligibilityPolicy.check(latest_revision=latest.revision, requested_revision=expected_revision, verification=full_verification, findings=list(self.repository.findings.values()), decisions=list(self.repository.decisions), source=(latest.source_id, latest.source_version))
            if idempotency_key:
                self._bind_idempotency("approve", idempotency_key, json.dumps({"noteId": note_id, "revision": expected_revision, "verification": full_verification.full_verification_id}, sort_keys=True))
            disposition = NoteDisposition(dispositionId=f"disposition-{self.id_factory()}", noteId=note_id, noteRevision=expected_revision, kind="APPROVED", reviewerLabel=reviewer_label, reason=rationale, fullVerificationId=full_verification.full_verification_id, decidedAt=self.clock())
            self.repository.dispositions.append(disposition)
            self.repository.persist_disposition(disposition)
            self.repository.append_event(self._event(note_id, expected_revision, reviewer_label, "NOTE_APPROVED", "DISPOSITION", disposition.disposition_id, (full_verification.full_verification_id,), rationale))
            return disposition

    def reject(self, note_id: str, *, expected_revision: int, reviewer_label: str, reason: str, idempotency_key: str | None = None) -> NoteDisposition:
        with self.repository._lock:
            latest = self.get_note(note_id)
            if latest.revision != expected_revision:
                raise ReviewServiceError("STALE_REVISION")
            if idempotency_key:
                self._bind_idempotency("reject", idempotency_key, json.dumps({"noteId": note_id, "revision": expected_revision, "reason": reason}, sort_keys=True))
            disposition = NoteDisposition(dispositionId=f"disposition-{self.id_factory()}", noteId=note_id, noteRevision=expected_revision, kind="REJECTED", reviewerLabel=reviewer_label, reason=reason, decidedAt=self.clock())
            self.repository.dispositions.append(disposition)
            self.repository.persist_disposition(disposition)
            self.repository.append_event(self._event(note_id, expected_revision, reviewer_label, "NOTE_REJECTED", "DISPOSITION", disposition.disposition_id, rationale=reason))
            return disposition

    def audit(self, note_id: str):
        return self.repository.audit(note_id)

    def context(self, note_id: str, transcript_text: str):
        note = self.get_note(note_id)
        findings = tuple(f for f in self.repository.findings.values() if f.note_id == note_id and f.note_revision == note.revision)
        decisions = tuple(d for d in self.repository.decisions if d.note_id == note_id)
        suggestions = tuple(s for s in self.repository.suggestions.values() if s.note_id == note_id and s.base_revision == note.revision)
        verification = next((v for v in self.repository.verifications.values() if v.note_id == note_id and v.note_revision == note.revision), None)
        return {"contractVersion": "REVIEW-AUDIT-CONTRACT-v1", "noteId": note_id, "revision": note.revision, "latestRevision": self.repository.latest[note_id], "noteStatus": "REJECTED" if any(d.note_id == note_id and d.kind == "REJECTED" for d in self.repository.dispositions) else "IN_REVIEW", "source": {"sourceId": note.source_id, "sourceVersion": note.source_version}, "transcriptText": transcript_text, "candidateNote": note.content, "findings": [f.model_dump(mode="json", by_alias=True) for f in findings], "decisions": [d.model_dump(mode="json", by_alias=True) for d in decisions], "suggestions": [s.model_dump(mode="json", by_alias=True) for s in suggestions], "fullVerification": verification.model_dump(mode="json", by_alias=True) if verification else None, "approvalEligible": False}

    def _bind_idempotency(self, operation: str, key: str, payload: str) -> None:
        try:
            self.repository.bind_idempotency(operation, key, hashlib.sha256(payload.encode()).hexdigest())
        except ReviewRepositoryError as error:
            raise ReviewServiceError(str(error)) from error
