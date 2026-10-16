from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from .approval import ApprovalEligibilityPolicy, ReviewServiceError
from .contracts import AuditEvent, ClaimReverificationResponse, EvidenceDisplay, FullNoteVerification, NoteDisposition, ReviewDecision, ReviewFinding, SuggestedCorrection
from .repository import InMemoryReviewRepository, ReviewRepositoryError


@dataclass(frozen=True)
class NoteRecord:
    note_id: str
    revision: int
    source_id: str
    source_version: int
    content: str


class ReviewService:
    def __init__(self, repository: InMemoryReviewRepository | None = None, *, clock=None, id_factory=None, note_revision_writer: Callable[..., Any] | None = None) -> None:
        self.repository = repository or InMemoryReviewRepository()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.id_factory = id_factory or (lambda: str(uuid4()))
        self.note_revision_writer = note_revision_writer
        self.claim_evidence: dict[tuple[str, int, str], EvidenceDisplay] = {}

    def attach_note_revision_writer(self, writer: Callable[..., Any]) -> None:
        """Attach the canonical nursing-note revision writer at composition time."""
        self.note_revision_writer = writer

    def record_claim_evidence(self, note_id: str, revision: int, claim_id: str, evidence: EvidenceDisplay) -> None:
        """Project supported evidence for display without creating a review finding."""
        self.claim_evidence[(note_id, revision, claim_id)] = evidence

    def _event(self, note_id: str, revision: int, actor: str, event_type: str, target_type: str, target_id: str, references=(), rationale=None) -> AuditEvent:
        payload = json.dumps({"eventType": event_type, "targetId": target_id, "references": list(references)}, sort_keys=True)
        return AuditEvent(eventId=f"event-{self.id_factory()}", sequence=len(self.repository.audit(note_id)) + 1, occurredAt=self.clock(), actorLabel=actor, eventType=event_type, noteId=note_id, noteRevision=revision, targetType=target_type, targetId=target_id, references=tuple(references), payloadDigest=hashlib.sha256(payload.encode()).hexdigest(), rationale=rationale)

    def seed_note(self, note_id: str, source_id: str, source_version: int, content: str) -> NoteRecord:
        if note_id in self.repository.latest:
            raise ReviewServiceError("NOTE_ALREADY_EXISTS")
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
            if idempotency_key:
                self._bind_idempotency("save-revision", idempotency_key, json.dumps({"noteId": note_id, "revision": expected_revision, "content": content, "reviewerLabel": reviewer_label}, sort_keys=True))
                replay = self.repository.get_replay("save-revision", idempotency_key)
                if replay is not None:
                    return replay
            latest = self.get_note(note_id)
            if any(disposition.note_id == note_id and disposition.kind == "REJECTED" for disposition in self.repository.dispositions):
                raise ReviewServiceError("FINAL_DISPOSITION_IMMUTABLE")
            if latest.revision != expected_revision:
                raise ReviewServiceError("STALE_REVISION")
                replay = self.repository.get_replay("save-revision", idempotency_key)
                if replay is not None:
                    return replay
            if self.note_revision_writer is not None:
                try:
                    canonical = self.note_revision_writer(
                        note_id,
                        content,
                        expected_revision=expected_revision,
                        requested_by=reviewer_label,
                    )
                except Exception as error:
                    code = getattr(getattr(error, "code", None), "value", None)
                    raise ReviewServiceError(code or "NOTE_REVISION_PERSISTENCE_FAILED") from error
                if (
                    canonical.note_id != note_id
                    or canonical.revision != latest.revision + 1
                    or canonical.source_id != latest.source_id
                    or canonical.source_version != latest.source_version
                ):
                    raise ReviewServiceError("PROVENANCE_CONFLICT")
                successor = NoteRecord(
                    canonical.note_id,
                    canonical.revision,
                    canonical.source_id,
                    canonical.source_version,
                    canonical.content,
                )
            else:
                successor = NoteRecord(note_id, latest.revision + 1, latest.source_id, latest.source_version, content)
            self.repository.notes[(note_id, successor.revision)] = successor
            self.repository.latest[note_id] = successor.revision
            self.repository.persist_note(successor)
            self.repository.append_event(self._event(note_id, successor.revision, reviewer_label, "NOTE_REVISION_CREATED", "NOTE_REVISION", f"{note_id}:r{successor.revision}", (f"{note_id}:r{latest.revision}",)))
            if idempotency_key:
                self.repository.set_replay("save-revision", idempotency_key, successor)
            return successor

    def add_finding(self, finding: ReviewFinding) -> None:
        note = self.get_note(finding.note_id, finding.note_revision)
        if (note.source_id, note.source_version) != (finding.source_id, finding.source_version):
            raise ReviewServiceError("PROVENANCE_CONFLICT")
        self.repository.persist_finding(finding)
        self.repository.findings[finding.review_finding_id] = finding
        self.repository.append_event(self._event(finding.note_id, finding.note_revision, "SYSTEM", "FINDING_IMPORTED", "REVIEW_FINDING", finding.review_finding_id, tuple(filter(None, (finding.origin_run_id, finding.origin_finding_id)))))

    def add_suggestion(self, suggestion: SuggestedCorrection) -> None:
        note = self.get_note(suggestion.note_id, suggestion.base_revision)
        finding = self.repository.findings.get(suggestion.finding_id)
        if suggestion.support_status == "USABLE" and finding is not None and (finding.note_id != suggestion.note_id or finding.note_revision != suggestion.base_revision):
            raise ReviewServiceError("FINDING_NOT_FOUND")
        if suggestion.support_status == "USABLE" and not suggestion.support_spans:
            raise ReviewServiceError("SUGGESTION_NOT_USABLE")
        span = suggestion.target_note_span
        if note.content[span.start_code_point:span.end_code_point_exclusive] != span.text:
            raise ReviewServiceError("SUGGESTION_TARGET_MISMATCH")
        if any((item.source_id, item.source_version) != (note.source_id, note.source_version) for item in suggestion.support_spans):
            raise ReviewServiceError("PROVENANCE_CONFLICT")
        self.repository.persist_suggestion(suggestion)
        self.repository.suggestions[suggestion.suggestion_id] = suggestion
        self.repository.append_event(self._event(suggestion.note_id, suggestion.base_revision, "SYSTEM", "SUGGESTION_RECORDED", "SUGGESTION", suggestion.suggestion_id, (suggestion.finding_id,)))

    def accept_suggestion(self, note_id: str, *, suggestion_id: str, expected_revision: int, reviewer_label: str, idempotency_key: str | None = None) -> NoteRecord:
        if idempotency_key:
            self._bind_idempotency("accept-suggestion", idempotency_key, json.dumps({"noteId": note_id, "suggestionId": suggestion_id, "expectedRevision": expected_revision, "reviewerLabel": reviewer_label}, sort_keys=True))
            replay = self.repository.get_replay("accept-suggestion", idempotency_key)
            if replay is not None:
                return replay
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
        successor = self.save_revision(note_id, expected_revision=expected_revision, content=note.content[:start] + suggestion.replacement + note.content[end:], reviewer_label=reviewer_label)
        if idempotency_key:
            self.repository.set_replay("accept-suggestion", idempotency_key, successor)
        return successor

    def record_decision(self, note_id: str, finding_id: str, *, expected_revision: int, kind: str, reviewer_label: str, rationale: str | None = None, suggestion_id: str | None = None, idempotency_key: str | None = None) -> ReviewDecision:
        allowed = {"ACKNOWLEDGED", "DISPUTED", "ADJUDICATED", "SUGGESTION_ACCEPTED", "SUGGESTION_REJECTED"}
        if kind not in allowed:
            raise ReviewServiceError("INVALID_REQUEST")
        if idempotency_key:
            self._bind_idempotency("finding-decision", idempotency_key, json.dumps({"noteId": note_id, "findingId": finding_id, "revision": expected_revision, "kind": kind, "suggestionId": suggestion_id, "rationale": rationale, "reviewerLabel": reviewer_label}, sort_keys=True))
            replay = self.repository.get_replay("finding-decision", idempotency_key)
            if replay is not None:
                return replay
        finding = self.repository.findings.get(finding_id)
        if finding is None or finding.note_id != note_id:
            raise ReviewServiceError("FINDING_NOT_FOUND")
        if finding.note_revision != expected_revision or self.get_note(note_id).revision != expected_revision:
            raise ReviewServiceError("STALE_REVISION")
        if kind in {"DISPUTED", "ADJUDICATED", "SUGGESTION_REJECTED"} and not rationale or not reviewer_label.strip():
            raise ReviewServiceError("INVALID_REQUEST")
        successor_revision = None
        if kind == "SUGGESTION_ACCEPTED":
            if not suggestion_id:
                raise ReviewServiceError("SUGGESTION_NOT_USABLE")
            suggestion = self.repository.suggestions.get(suggestion_id)
            if suggestion is None or suggestion.finding_id != finding_id:
                raise ReviewServiceError("SUGGESTION_NOT_FOUND")
            successor = self.accept_suggestion(note_id, suggestion_id=suggestion_id, expected_revision=expected_revision, reviewer_label=reviewer_label)
            successor_revision = successor.revision
            outcome = "RESOLVED"
        elif kind == "SUGGESTION_REJECTED":
            if not suggestion_id:
                raise ReviewServiceError("SUGGESTION_NOT_FOUND")
            suggestion = self.repository.suggestions.get(suggestion_id)
            if suggestion is None or suggestion.finding_id != finding_id or suggestion.note_id != note_id or suggestion.base_revision != expected_revision:
                raise ReviewServiceError("SUGGESTION_NOT_FOUND")
            outcome = "NO_STATE_CHANGE"
        else:
            outcome = "NO_STATE_CHANGE" if kind in {"ACKNOWLEDGED", "DISPUTED"} or finding.severity == "CRITICAL" else "ADJUDICATED"
        decision = ReviewDecision(reviewDecisionId=f"decision-{self.id_factory()}", findingId=finding_id, noteId=note_id, noteRevision=expected_revision, kind=kind, outcome=outcome, reviewerLabel=reviewer_label, rationale=rationale, successorRevision=successor_revision, suggestionId=suggestion_id, idempotencyKey=idempotency_key, recordedAt=self.clock())
        self.repository.decisions.append(decision)
        self.repository.persist_decision(decision)
        self.repository.append_event(self._event(note_id, expected_revision, reviewer_label, "FINDING_DECISION_RECORDED", "REVIEW_DECISION", decision.review_decision_id, (finding_id,), rationale))
        if idempotency_key:
            self.repository.set_replay("finding-decision", idempotency_key, decision)
        return decision

    def persist_verification(self, verification: FullNoteVerification) -> FullNoteVerification:
        note = self.get_note(verification.note_id, verification.note_revision)
        if (note.source_id, note.source_version) != (verification.source.source_id, verification.source.source_version):
            raise ReviewServiceError("PROVENANCE_CONFLICT")
        current = self.repository.verifications.get(verification.full_verification_id)
        if current is not None:
            if current != verification:
                raise ReviewServiceError("IMMUTABLE_RECORD_CONFLICT")
            return verification
        self.repository.verifications[verification.full_verification_id] = verification
        self.repository.persist_verification(verification)
        self.repository.append_event(self._event(verification.note_id, verification.note_revision, "SYSTEM", "FULL_VERIFICATION_RECORDED", "FULL_VERIFICATION", verification.full_verification_id, (verification.claim_set_id, verification.evidence_run_id, verification.deterministic_validation_run_id, verification.coverage_run_id), verification.failure_message))
        return verification

    def approve(self, note_id: str, *, expected_revision: int, full_verification: FullNoteVerification, reviewer_label: str, rationale: str | None = None, idempotency_key: str | None = None) -> NoteDisposition:
        with self.repository._lock:
            if not reviewer_label.strip():
                raise ReviewServiceError("INVALID_REQUEST")
            if idempotency_key:
                self._bind_idempotency("approve", idempotency_key, json.dumps({"noteId": note_id, "revision": expected_revision, "verification": full_verification.full_verification_id, "reviewerLabel": reviewer_label, "rationale": rationale}, sort_keys=True))
                replay = self.repository.get_replay("approve", idempotency_key)
                if replay is not None:
                    return replay
            latest = self.get_note(note_id)
            if latest.revision != expected_revision:
                raise ReviewServiceError("STALE_REVISION")
            if any(disposition.note_id == note_id and disposition.note_revision == expected_revision and disposition.kind == "APPROVED" for disposition in self.repository.dispositions):
                raise ReviewServiceError("REVISION_ALREADY_APPROVED")
            persisted = self.repository.verifications.get(full_verification.full_verification_id)
            if persisted != full_verification:
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
            ApprovalEligibilityPolicy.check(latest_revision=latest.revision, requested_revision=expected_revision, verification=full_verification, findings=list(self.repository.findings.values()), decisions=list(self.repository.decisions), source=(latest.source_id, latest.source_version))
            disposition = NoteDisposition(dispositionId=f"disposition-{self.id_factory()}", noteId=note_id, noteRevision=expected_revision, kind="APPROVED", reviewerLabel=reviewer_label, reason=rationale, fullVerificationId=full_verification.full_verification_id, eligibilityPolicyVersion=ApprovalEligibilityPolicy.version, decidedAt=self.clock())
            self.repository.dispositions.append(disposition)
            self.repository.persist_disposition(disposition)
            self.repository.append_event(self._event(note_id, expected_revision, reviewer_label, "NOTE_APPROVED", "DISPOSITION", disposition.disposition_id, (full_verification.full_verification_id,), rationale))
            if idempotency_key:
                self.repository.set_replay("approve", idempotency_key, disposition)
            return disposition

    def reject(self, note_id: str, *, expected_revision: int, reviewer_label: str, reason: str, idempotency_key: str | None = None) -> NoteDisposition:
        with self.repository._lock:
            if idempotency_key:
                self._bind_idempotency("reject", idempotency_key, json.dumps({"noteId": note_id, "revision": expected_revision, "reviewerLabel": reviewer_label, "reason": reason}, sort_keys=True))
                replay = self.repository.get_replay("reject", idempotency_key)
                if replay is not None:
                    return replay
            latest = self.get_note(note_id)
            if latest.revision != expected_revision:
                raise ReviewServiceError("STALE_REVISION")
            if any(disposition.note_id == note_id for disposition in self.repository.dispositions):
                raise ReviewServiceError("FINAL_DISPOSITION_IMMUTABLE")
            if not reviewer_label.strip() or not reason.strip():
                raise ReviewServiceError("INVALID_REQUEST")
            disposition = NoteDisposition(dispositionId=f"disposition-{self.id_factory()}", noteId=note_id, noteRevision=expected_revision, kind="REJECTED", reviewerLabel=reviewer_label, reason=reason, eligibilityPolicyVersion=ApprovalEligibilityPolicy.version, decidedAt=self.clock())
            self.repository.dispositions.append(disposition)
            self.repository.persist_disposition(disposition)
            self.repository.append_event(self._event(note_id, expected_revision, reviewer_label, "NOTE_REJECTED", "DISPOSITION", disposition.disposition_id, rationale=reason))
            if idempotency_key:
                self.repository.set_replay("reject", idempotency_key, disposition)
            return disposition

    def audit(self, note_id: str):
        return self.repository.audit(note_id)

    def record_claim_feedback(self, note_id: str, *, note_revision: int, claim_id: str, reviewer_label: str, idempotency_key: str, claim_reverifier) -> ClaimReverificationResponse:
        note = self.get_note(note_id)
        if note.revision != note_revision:
            raise ReviewServiceError("STALE_REVISION")
        digest_payload = json.dumps({"noteId": note_id, "noteRevision": note_revision, "claimId": claim_id, "reviewerLabel": reviewer_label}, sort_keys=True)
        self._bind_idempotency("claim-reverification", idempotency_key, digest_payload)
        replay = self.repository.get_replay("claim-reverification", idempotency_key)
        if replay is not None:
            return replay
        run_id = claim_reverifier(note_id, note_revision, claim_id)
        result = ClaimReverificationResponse(
            reviewVerificationId=f"claim-feedback-{run_id}",
            noteId=note_id,
            noteRevision=note_revision,
            claimId=claim_id,
            source={"sourceId": note.source_id, "sourceVersion": note.source_version},
            upstreamVerificationRunId=run_id,
            status="SUCCEEDED",
            approvalEligible=False,
        )
        self.repository.claim_feedback[result.review_verification_id] = result
        self.repository.persist_claim_feedback(result)
        self.repository.append_event(self._event(note_id, note_revision, reviewer_label, "CLAIM_REVERIFICATION_RECORDED", "CLAIM_REVERIFICATION", result.review_verification_id, (claim_id, run_id)))
        self.repository.set_replay("claim-reverification", idempotency_key, result)
        return result

    def context(self, note_id: str, transcript_text: str, revision: int | None = None):
        note = self.get_note(note_id, revision)
        findings = tuple(f for f in self.repository.findings.values() if f.note_id == note_id and f.note_revision == note.revision)
        decisions = tuple(d for d in self.repository.decisions if d.note_id == note_id)
        suggestions = tuple(s for s in self.repository.suggestions.values() if s.note_id == note_id and s.base_revision == note.revision)
        verification = next((v for v in reversed(tuple(self.repository.verifications.values())) if v.note_id == note_id and v.note_revision == note.revision), None)
        disposition = next((d for d in reversed(self.repository.dispositions) if d.note_id == note_id and d.note_revision == note.revision), None)
        status = disposition.kind if disposition else ("ELIGIBLE_FOR_APPROVAL" if verification and verification.status == "VALID" else ("AWAITING_FULL_VERIFICATION" if note.revision > 1 else "IN_REVIEW"))
        approval_eligible = False
        if verification and verification.status == "VALID":
            try:
                ApprovalEligibilityPolicy.check(latest_revision=self.repository.latest[note_id], requested_revision=note.revision, verification=verification, findings=list(self.repository.findings.values()), decisions=list(self.repository.decisions), source=(note.source_id, note.source_version))
                approval_eligible = True
            except ReviewServiceError:
                pass
        claim_result = None
        claim_reader = getattr(self, "claim_reader", None)
        if claim_reader is not None:
            claim_result = claim_reader(note_id, note.revision)
        extracted_claims = []
        for claim in getattr(claim_result, "claims", ()):
            claim_findings = [f for f in findings if f.claim_id == claim.id]
            primary = next((f for f in claim_findings if f.upstream_status in {"SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "UNCERTAIN"}), None)
            projected_evidence = self.claim_evidence.get((note_id, note.revision, claim.id))
            extracted_claims.append({
                "claimId": claim.id,
                "claimText": claim.claim_text,
                "statementSpan": {"startCodePoint": claim.statement_span.start_code_point, "endCodePointExclusive": claim.statement_span.end_code_point_exclusive, "text": claim.statement_span.text},
                "verificationState": "FAILED" if verification and verification.status != "VALID" else ("VERIFIED" if verification else "NOT_VERIFIED"),
                "evidenceStatus": primary.upstream_status if primary else None,
                "explanation": primary.explanation if primary else None,
                "evidence": primary.evidence.model_dump(mode="json", by_alias=True) if primary else (projected_evidence.model_dump(mode="json", by_alias=True) if projected_evidence else None),
                "verificationRunId": primary.origin_run_id if primary else (verification.evidence_run_id if verification else None),
                "findingIds": tuple(f.review_finding_id for f in claim_findings),
            })
        approval = None
        if disposition and disposition.kind == "APPROVED":
            approval_event = next((e for e in reversed(self.repository.audit(note_id)) if e.target_id == disposition.disposition_id), None)
            approval = {"dispositionId": disposition.disposition_id, "noteId": note_id, "noteRevision": disposition.note_revision, "reviewerLabel": disposition.reviewer_label, "decidedAt": disposition.decided_at, "fullVerificationId": disposition.full_verification_id, "auditEventId": approval_event.event_id if approval_event else "unknown", "meaning": "A caregiver has reviewed and accepted this specific verified revision of the nursing note."}
        return {"contractVersion": "REVIEW-AUDIT-CONTRACT-v1", "noteId": note_id, "revision": note.revision, "latestRevision": self.repository.latest[note_id], "noteStatus": status, "source": {"sourceId": note.source_id, "sourceVersion": note.source_version}, "transcriptText": transcript_text, "candidateNote": note.content, "extractedClaims": extracted_claims, "findings": [f.model_dump(mode="json", by_alias=True) for f in findings], "decisions": [d.model_dump(mode="json", by_alias=True) for d in decisions], "suggestions": [s.model_dump(mode="json", by_alias=True) for s in suggestions], "fullVerification": verification.model_dump(mode="json", by_alias=True) if verification else None, "approvalEligible": approval_eligible, "approval": approval}

    def _bind_idempotency(self, operation: str, key: str, payload: str) -> str:
        try:
            digest = hashlib.sha256(payload.encode()).hexdigest()
            self.repository.bind_idempotency(operation, key, digest)
            return digest
        except ReviewRepositoryError as error:
            raise ReviewServiceError(str(error)) from error
