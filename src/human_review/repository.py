from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any
import sqlite3
from pathlib import Path

from .contracts import AuditEvent, ClaimReverificationResponse, FullNoteVerification, NoteDisposition, ReviewDecision, ReviewFinding, SuggestedCorrection


class ReviewRepositoryError(RuntimeError):
    pass


class InMemoryReviewRepository:
    """Append-only review store used by the synthetic local PoC."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.notes: dict[tuple[str, int], Any] = {}
        self.latest: dict[str, int] = {}
        self.findings: dict[str, ReviewFinding] = {}
        self.decisions: list[ReviewDecision] = []
        self.suggestions: dict[str, SuggestedCorrection] = {}
        self.verifications: dict[str, FullNoteVerification] = {}
        self.claim_feedback: dict[str, ClaimReverificationResponse] = {}
        self.dispositions: list[NoteDisposition] = []
        self.events: dict[str, list[AuditEvent]] = {}
        self.idempotency: dict[tuple[str, str], str] = {}
        self.replays: dict[tuple[str, str], Any] = {}

    def append_event(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            events = self.events.setdefault(event.note_id, [])
            if any(existing.event_id == event.event_id for existing in events):
                raise ReviewRepositoryError("duplicate audit event")
            expected = len(events) + 1
            if event.sequence != expected:
                raise ReviewRepositoryError("audit sequence conflict")
            events.append(deepcopy(event))
            return deepcopy(event)

    def audit(self, note_id: str) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(deepcopy(self.events.get(note_id, [])))

    def bind_idempotency(self, operation: str, key: str, digest: str) -> None:
        with self._lock:
            existing = self.idempotency.get((operation, key))
            if existing is not None and existing != digest:
                raise ReviewRepositoryError("IDEMPOTENCY_KEY_CONFLICT")
            self.idempotency[(operation, key)] = digest

    def idempotency_digest(self, operation: str, key: str) -> str | None:
        with self._lock:
            return self.idempotency.get((operation, key))

    def get_replay(self, operation: str, key: str) -> Any | None:
        with self._lock:
            return deepcopy(self.replays.get((operation, key)))

    def set_replay(self, operation: str, key: str, value: Any) -> None:
        with self._lock:
            self.replays[(operation, key)] = deepcopy(value)

    def persist_note(self, note: Any) -> None:
        return None

    def persist_finding(self, finding: ReviewFinding) -> None:
        existing = self.findings.get(finding.review_finding_id)
        if existing is not None and existing != finding:
            raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")

    def persist_decision(self, decision: ReviewDecision) -> None:
        if any(existing.review_decision_id == decision.review_decision_id and existing != decision for existing in self.decisions):
            raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")

    def persist_suggestion(self, suggestion: SuggestedCorrection) -> None:
        existing = self.suggestions.get(suggestion.suggestion_id)
        if existing is not None and existing != suggestion:
            raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")

    def persist_verification(self, verification: FullNoteVerification) -> None:
        existing = self.verifications.get(verification.full_verification_id)
        if existing is not None and existing != verification:
            raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")

    def persist_disposition(self, disposition: NoteDisposition) -> None:
        if any(existing.disposition_id == disposition.disposition_id and existing != disposition for existing in self.dispositions):
            raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")

    def persist_claim_feedback(self, feedback: ClaimReverificationResponse) -> None:
        existing = self.claim_feedback.get(feedback.review_verification_id)
        if existing is not None and existing != feedback:
            raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")


class SQLiteReviewRepository(InMemoryReviewRepository):
    """Local durable audit boundary; review records remain append-only."""

    def __init__(self, database_path: str | Path = "data/human_review.sqlite3") -> None:
        super().__init__()
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                note_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(note_id, sequence)
            )
        """)
        for table, key in (("notes", "note_key"), ("findings", "finding_id"), ("decisions", "decision_id"), ("suggestions", "suggestion_id"), ("verifications", "verification_id"), ("claim_feedback", "feedback_id"), ("dispositions", "disposition_id")):
            self._connection.execute(f"CREATE TABLE IF NOT EXISTS {table} ({key} TEXT PRIMARY KEY, payload_json TEXT NOT NULL)")
        self._connection.execute("CREATE TABLE IF NOT EXISTS idempotency (operation TEXT NOT NULL, key TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(operation, key))")
        self._connection.commit()
        self._load_events()
        self._load_entities()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _load_events(self) -> None:
        import json
        from .contracts import AuditEvent
        for row in self._connection.execute("SELECT payload_json FROM audit_events ORDER BY note_id, sequence"):
            event = AuditEvent.model_validate_json(row["payload_json"])
            self.events.setdefault(event.note_id, []).append(event)

    def _load_entities(self) -> None:
        import json
        from .service import NoteRecord
        for row in self._connection.execute("SELECT note_key, payload_json FROM notes"):
            note = json.loads(row["payload_json"])
            record = NoteRecord(**note)
            self.notes[(record.note_id, record.revision)] = record
            self.latest[record.note_id] = max(record.revision, self.latest.get(record.note_id, 0))
        for row in self._connection.execute("SELECT payload_json FROM findings"):
            finding = ReviewFinding.model_validate_json(row["payload_json"])
            self.findings[finding.review_finding_id] = finding
        for row in self._connection.execute("SELECT payload_json FROM decisions"):
            self.decisions.append(ReviewDecision.model_validate_json(row["payload_json"]))
        for row in self._connection.execute("SELECT payload_json FROM suggestions"):
            suggestion = SuggestedCorrection.model_validate_json(row["payload_json"])
            self.suggestions[suggestion.suggestion_id] = suggestion
        for row in self._connection.execute("SELECT payload_json FROM verifications"):
            verification = FullNoteVerification.model_validate_json(row["payload_json"])
            self.verifications[verification.full_verification_id] = verification
        for row in self._connection.execute("SELECT payload_json FROM claim_feedback"):
            feedback = ClaimReverificationResponse.model_validate_json(row["payload_json"])
            self.claim_feedback[feedback.review_verification_id] = feedback
        for row in self._connection.execute("SELECT payload_json FROM dispositions"):
            self.dispositions.append(NoteDisposition.model_validate_json(row["payload_json"]))
        for row in self._connection.execute("SELECT operation, key, digest FROM idempotency"):
            self.idempotency[(row["operation"], row["key"])] = row["digest"]

    def _persist_json(self, table: str, key_column: str, key: str, payload: str) -> None:
        try:
            self._connection.execute(f"INSERT INTO {table}({key_column}, payload_json) VALUES (?, ?)", (key, payload))
            self._connection.commit()
        except sqlite3.IntegrityError:
            existing = self._connection.execute(f"SELECT payload_json FROM {table} WHERE {key_column} = ?", (key,)).fetchone()
            if existing is None or existing["payload_json"] != payload:
                raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")

    def persist_note(self, note: Any) -> None:
        import json
        self._persist_json("notes", "note_key", f"{note.note_id}:{note.revision}", json.dumps({"note_id": note.note_id, "revision": note.revision, "source_id": note.source_id, "source_version": note.source_version, "content": note.content}, sort_keys=True))

    def persist_finding(self, finding: ReviewFinding) -> None:
        self._require_note(finding.note_id, finding.note_revision)
        self._persist_json("findings", "finding_id", finding.review_finding_id, finding.model_dump_json(by_alias=True))

    def persist_decision(self, decision: ReviewDecision) -> None:
        self._require_note(decision.note_id, decision.note_revision)
        if decision.finding_id not in self.findings:
            raise ReviewRepositoryError("FINDING_NOT_FOUND")
        self._persist_json("decisions", "decision_id", decision.review_decision_id, decision.model_dump_json(by_alias=True))

    def persist_suggestion(self, suggestion: SuggestedCorrection) -> None:
        self._require_note(suggestion.note_id, suggestion.base_revision)
        self._persist_json("suggestions", "suggestion_id", suggestion.suggestion_id, suggestion.model_dump_json(by_alias=True))

    def persist_verification(self, verification: FullNoteVerification) -> None:
        self._require_note(verification.note_id, verification.note_revision)
        self._persist_json("verifications", "verification_id", verification.full_verification_id, verification.model_dump_json(by_alias=True))

    def persist_claim_feedback(self, feedback: ClaimReverificationResponse) -> None:
        self._require_note(feedback.note_id, feedback.note_revision)
        self._persist_json("claim_feedback", "feedback_id", feedback.review_verification_id, feedback.model_dump_json(by_alias=True))

    def persist_disposition(self, disposition: NoteDisposition) -> None:
        self._require_note(disposition.note_id, disposition.note_revision)
        if any(existing.note_id == disposition.note_id for existing in self.dispositions if existing.disposition_id != disposition.disposition_id):
            raise ReviewRepositoryError("FINAL_DISPOSITION_IMMUTABLE")
        if disposition.kind == "APPROVED" and disposition.full_verification_id not in self.verifications:
            raise ReviewRepositoryError("APPROVAL_PRECONDITION_FAILED")
        self._persist_json("dispositions", "disposition_id", disposition.disposition_id, disposition.model_dump_json(by_alias=True))

    def _require_note(self, note_id: str, revision: int) -> None:
        if (note_id, revision) not in self.notes:
            raise ReviewRepositoryError("NOTE_NOT_FOUND")

    def append_event(self, event: AuditEvent) -> AuditEvent:
        import json
        saved = super().append_event(event)
        try:
            self._connection.execute(
                "INSERT INTO audit_events(event_id, note_id, sequence, payload_json) VALUES (?, ?, ?, ?)",
                (event.event_id, event.note_id, event.sequence, event.model_dump_json(by_alias=True)),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self.events[event.note_id].pop()
            raise ReviewRepositoryError("AUDIT_EVENT_CONFLICT") from error
        return saved

    def bind_idempotency(self, operation: str, key: str, digest: str) -> None:
        super().bind_idempotency(operation, key, digest)
        try:
            self._connection.execute("INSERT INTO idempotency(operation, key, digest) VALUES (?, ?, ?)", (operation, key, digest))
            self._connection.commit()
        except sqlite3.IntegrityError:
            existing = self._connection.execute("SELECT digest FROM idempotency WHERE operation = ? AND key = ?", (operation, key)).fetchone()
            if existing is None or existing["digest"] != digest:
                raise ReviewRepositoryError("IDEMPOTENCY_KEY_CONFLICT")
