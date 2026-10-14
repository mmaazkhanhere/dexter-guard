"""PostgreSQL persistence adapters for the deployed modular monolith.

The application services intentionally keep their existing repository
protocols. These adapters therefore expose the same small interfaces as the
in-memory/SQLite repositories while storing immutable records in PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from evaluation.contracts import BenchmarkDataset, EvaluationRun
from evaluation.repository import EvaluationRepositoryError, IdempotencyConflict
from human_review.contracts import (
    AuditEvent,
    ClaimReverificationResponse,
    FullNoteVerification,
    NoteDisposition,
    ReviewDecision,
    ReviewFinding,
    SuggestedCorrection,
)
from human_review.repository import InMemoryReviewRepository, ReviewRepositoryError
from human_review.service import NoteRecord
from nursing_notes.contracts import NoteRevisionRecord
from nursing_notes.errors import NoteError, NoteErrorCode
from source_ingestion.contracts import SourceDocument
from source_ingestion.errors import ErrorCode, SourceError


class _PostgresDatabase:
    """Open a fresh transaction-scoped connection for each operation.

    Vercel functions can be frozen and resumed after the database connection
    has been closed by the provider or by a pooler. Keeping a raw connection
    on a repository therefore creates intermittent ``connection is closed``
    failures. A short-lived connection also works correctly with Neon-style
    pooler URLs and keeps each transaction isolated across invocations.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._lock = RLock()
        raw_timeout = os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5")
        try:
            parsed_timeout = int(raw_timeout)
        except ValueError:
            parsed_timeout = 5
        self.connect_timeout = min(max(parsed_timeout, 1), 30)

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection[Any]]:
        with self._lock:
            with psycopg.connect(
                self.database_url,
                row_factory=dict_row,
                connect_timeout=self.connect_timeout,
            ) as connection:
                with connection.transaction():
                    yield connection

    def check(self) -> bool:
        try:
            with self.transaction() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except psycopg.Error:
            return False


def run_migrations(database_url: str) -> None:
    """Apply checked-in SQL migrations exactly once per database."""

    migration_dir = Path(__file__).resolve().parents[2] / "migrations"
    migrations = sorted(migration_dir.glob("*.sql"))
    if not migrations:
        raise RuntimeError(f"No database migrations found in {migration_dir}")
    database = _PostgresDatabase(database_url)
    with database.transaction() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for migration in migrations:
            version = migration.name
            applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s", (version,)
            ).fetchone()
            if applied:
                continue
            connection.execute(migration.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations(version) VALUES (%s)", (version,)
            )


class PostgresSourceRepository:
    def __init__(self, database_url: str) -> None:
        self._database = _PostgresDatabase(database_url)

    def create_initial(self, document: SourceDocument) -> SourceDocument:
        with self._database.transaction() as connection:
            existing = connection.execute(
                "SELECT 1 FROM source_documents WHERE source_id = %s AND source_version = %s",
                (document.source_id, document.source_version),
            ).fetchone()
            has_source = connection.execute(
                "SELECT 1 FROM source_documents WHERE source_id = %s LIMIT 1",
                (document.source_id,),
            ).fetchone()
            if existing or document.source_version != 1 or has_source:
                raise SourceError(
                    ErrorCode.DUPLICATE_SOURCE_VERSION,
                    "An initial source must use a new source ID at version 1.",
                    "source_id",
                )
            connection.execute(
                """
                INSERT INTO source_documents
                (source_id, source_version, resident_test_id, language, transcript_text, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    document.source_id,
                    document.source_version,
                    document.resident_test_id,
                    document.language,
                    document.transcript_text,
                    document.created_at,
                ),
            )
        return document.model_copy(deep=True)

    def ensure_initial(self, documents: Iterable[SourceDocument]) -> None:
        """Insert initial documents in one transaction without overwriting them."""

        pending = tuple(documents)
        if not pending:
            return
        with self._database.transaction() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO source_documents
                    (source_id, source_version, resident_test_id, language, transcript_text, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, source_version) DO NOTHING
                    """,
                    [
                        (
                            document.source_id,
                            document.source_version,
                            document.resident_test_id,
                            document.language,
                            document.transcript_text,
                            document.created_at,
                        )
                        for document in pending
                    ],
                )

    def create_next_version(
        self, source_id: str, expected_source_version: int, transcript_text: str, created_at: datetime
    ) -> SourceDocument:
        with self._database.transaction() as connection:
            latest = connection.execute(
                "SELECT * FROM source_documents WHERE source_id = %s ORDER BY source_version DESC LIMIT 1 FOR UPDATE",
                (source_id,),
            ).fetchone()
            if latest is None:
                raise SourceError(ErrorCode.SOURCE_NOT_FOUND, "The source ID does not exist.", "source_id")
            if latest["source_version"] != expected_source_version:
                raise SourceError(
                    ErrorCode.VERSION_CONFLICT,
                    "The expected source version is stale or conflicts with another revision.",
                    "expected_source_version",
                )
            document = SourceDocument(
                source_id=source_id,
                source_version=expected_source_version + 1,
                resident_test_id=latest["resident_test_id"],
                language=latest["language"],
                transcript_text=transcript_text,
                created_at=created_at,
            )
            try:
                connection.execute(
                    """
                    INSERT INTO source_documents
                    (source_id, source_version, resident_test_id, language, transcript_text, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        document.source_id,
                        document.source_version,
                        document.resident_test_id,
                        document.language,
                        document.transcript_text,
                        document.created_at,
                    ),
                )
            except UniqueViolation as error:
                raise SourceError(ErrorCode.VERSION_CONFLICT, "The next source version is already claimed.", "expected_source_version") from error
        return document

    def get(self, source_id: str, source_version: int) -> SourceDocument:
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM source_documents WHERE source_id = %s AND source_version = %s",
                (source_id, source_version),
            ).fetchone()
            if row is None:
                source_exists = connection.execute(
                    "SELECT 1 FROM source_documents WHERE source_id = %s LIMIT 1", (source_id,)
                ).fetchone()
                if source_exists is None:
                    raise SourceError(ErrorCode.SOURCE_NOT_FOUND, "The source ID does not exist.", "source_id")
                raise SourceError(ErrorCode.SOURCE_VERSION_NOT_FOUND, "The requested source version does not exist.", "source_version")
            return SourceDocument(
                source_id=row["source_id"], source_version=row["source_version"], resident_test_id=row["resident_test_id"],
                language=row["language"], transcript_text=row["transcript_text"], created_at=row["created_at"],
            )

    def source_exists(self, source_id: str) -> bool:
        with self._database.transaction() as connection:
            return connection.execute("SELECT 1 FROM source_documents WHERE source_id = %s LIMIT 1", (source_id,)).fetchone() is not None

    def version_exists(self, source_id: str, source_version: int) -> bool:
        with self._database.transaction() as connection:
            return connection.execute("SELECT 1 FROM source_documents WHERE source_id = %s AND source_version = %s", (source_id, source_version)).fetchone() is not None

    def close(self) -> None:
        return None


class PostgresNoteRepository:
    def __init__(self, database_url: str) -> None:
        self._database = _PostgresDatabase(database_url)

    def create(self, revision: NoteRevisionRecord) -> NoteRevisionRecord:
        with self._database.transaction() as connection:
            latest_row = connection.execute(
                "SELECT revision FROM note_revisions WHERE note_id = %s ORDER BY revision DESC LIMIT 1 FOR UPDATE",
                (revision.note_id,),
            ).fetchone()
            latest = latest_row["revision"] if latest_row else None
            if revision.revision == 1:
                valid = latest is None and revision.previous_revision_id is None
            else:
                valid = latest == revision.revision - 1 and revision.previous_revision_id == f"{revision.note_id}:r{latest}"
            if not valid:
                raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note predecessor is stale or invalid.")
            try:
                connection.execute(
                    """
                    INSERT INTO note_revisions
                    (note_id, revision, previous_revision_id, content, status, origin, source_id, source_version,
                     external_origin_json, validation_run_id, generation_run_id, model_id, prompt_version,
                     schema_version, ruleset_version, source_text_hash, normalization_policy, created_at, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        revision.note_id, revision.revision, revision.previous_revision_id, revision.content,
                        revision.status, revision.origin, revision.source_id, revision.source_version,
                        Jsonb(revision.external_origin.model_dump(mode="json", by_alias=True)) if revision.external_origin else None,
                        revision.validation_run_id, revision.generation_run_id, revision.model_id, revision.prompt_version,
                        revision.schema_version, revision.ruleset_version, revision.source_text_hash,
                        revision.normalization_policy, revision.created_at, revision.created_by,
                    ),
                )
                for index, fact in enumerate(revision.facts, start=1):
                    connection.execute(
                        "INSERT INTO nursing_facts(note_id, revision, fact_index, payload_json) VALUES (%s, %s, %s, %s)",
                        (revision.note_id, revision.revision, index, Jsonb(fact.model_dump(mode="json", by_alias=True))),
                    )
            except UniqueViolation as error:
                raise NoteError(NoteErrorCode.NOTE_VERSION_CONFLICT, "The note revision conflicts with stored data.") from error
        return revision.model_copy(deep=True)

    def get(self, note_id: str, revision: int | None = None) -> NoteRevisionRecord:
        with self._database.transaction() as connection:
            if revision is None:
                latest = connection.execute("SELECT MAX(revision) AS revision FROM note_revisions WHERE note_id = %s", (note_id,)).fetchone()
                revision = latest["revision"] if latest and latest["revision"] is not None else None
            row = connection.execute("SELECT * FROM note_revisions WHERE note_id = %s AND revision = %s", (note_id, revision)).fetchone() if revision is not None else None
            if row is None:
                raise NoteError(NoteErrorCode.NOTE_NOT_FOUND, "The requested note revision does not exist.")
            fact_rows = connection.execute("SELECT payload_json FROM nursing_facts WHERE note_id = %s AND revision = %s ORDER BY fact_index", (note_id, revision)).fetchall()
            payload = {
                "noteId": row["note_id"], "revision": row["revision"], "previousRevisionId": row["previous_revision_id"],
                "content": row["content"], "status": row["status"], "origin": row["origin"], "sourceId": row["source_id"],
                "sourceVersion": row["source_version"], "externalOrigin": row["external_origin_json"],
                "validationRunId": row["validation_run_id"], "facts": [item["payload_json"] for item in fact_rows],
                "generationRunId": row["generation_run_id"], "modelId": row["model_id"], "promptVersion": row["prompt_version"],
                "schemaVersion": row["schema_version"], "rulesetVersion": row["ruleset_version"], "sourceTextHash": row["source_text_hash"],
                "normalizationPolicy": row["normalization_policy"], "createdAt": row["created_at"], "createdBy": row["created_by"],
            }
            return NoteRevisionRecord.model_validate(payload)

    def count(self) -> int:
        with self._database.transaction() as connection:
            return int(connection.execute("SELECT COUNT(*) AS count FROM note_revisions").fetchone()["count"])

    def fact_count(self) -> int:
        with self._database.transaction() as connection:
            return int(connection.execute("SELECT COUNT(*) AS count FROM nursing_facts").fetchone()["count"])

    def close(self) -> None:
        return None


class PostgresReviewRepository(InMemoryReviewRepository):
    def __init__(self, database_url: str) -> None:
        super().__init__()
        self._database = _PostgresDatabase(database_url)
        self._load()

    def _load(self) -> None:
        with self._database.transaction() as connection:
            for row in connection.execute("SELECT payload_json FROM review_audit_events ORDER BY note_id, sequence"):
                event = AuditEvent.model_validate(row["payload_json"])
                self.events.setdefault(event.note_id, []).append(event)
            for row in connection.execute("SELECT payload_json FROM review_notes"):
                note = NoteRecord(**row["payload_json"])
                self.notes[(note.note_id, note.revision)] = note
                self.latest[note.note_id] = max(note.revision, self.latest.get(note.note_id, 0))
            for row in connection.execute("SELECT payload_json FROM review_findings"):
                finding = ReviewFinding.model_validate(row["payload_json"])
                self.findings[finding.review_finding_id] = finding
            for row in connection.execute("SELECT payload_json FROM review_decisions ORDER BY decision_id"):
                self.decisions.append(ReviewDecision.model_validate(row["payload_json"]))
            for row in connection.execute("SELECT payload_json FROM review_suggestions"):
                suggestion = SuggestedCorrection.model_validate(row["payload_json"])
                self.suggestions[suggestion.suggestion_id] = suggestion
            for row in connection.execute("SELECT payload_json FROM review_verifications"):
                verification = FullNoteVerification.model_validate(row["payload_json"])
                self.verifications[verification.full_verification_id] = verification
            for row in connection.execute("SELECT payload_json FROM review_claim_feedback"):
                feedback = ClaimReverificationResponse.model_validate(row["payload_json"])
                self.claim_feedback[feedback.review_verification_id] = feedback
            for row in connection.execute("SELECT payload_json FROM review_dispositions ORDER BY disposition_id"):
                self.dispositions.append(NoteDisposition.model_validate(row["payload_json"]))
            for row in connection.execute("SELECT operation, key, digest FROM review_idempotency"):
                self.idempotency[(row["operation"], row["key"])] = row["digest"]

    def _persist_json(self, table: str, key_column: str, key: str, payload: dict[str, Any]) -> None:
        with self._database.transaction() as connection:
            existing = connection.execute(f"SELECT payload_json FROM {table} WHERE {key_column} = %s", (key,)).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload:
                    raise ReviewRepositoryError("IMMUTABLE_RECORD_CONFLICT")
                return
            connection.execute(f"INSERT INTO {table}({key_column}, payload_json) VALUES (%s, %s)", (key, Jsonb(payload)))

    def persist_note(self, note: Any) -> None:
        super().persist_note(note)
        self._persist_json("review_notes", "note_key", f"{note.note_id}:{note.revision}", {
            "note_id": note.note_id, "revision": note.revision, "source_id": note.source_id,
            "source_version": note.source_version, "content": note.content,
        })

    def persist_finding(self, finding: ReviewFinding) -> None:
        super().persist_finding(finding)
        self._persist_json("review_findings", "finding_id", finding.review_finding_id, finding.model_dump(mode="json", by_alias=True))

    def persist_decision(self, decision: ReviewDecision) -> None:
        super().persist_decision(decision)
        self._persist_json("review_decisions", "decision_id", decision.review_decision_id, decision.model_dump(mode="json", by_alias=True))

    def persist_suggestion(self, suggestion: SuggestedCorrection) -> None:
        super().persist_suggestion(suggestion)
        self._persist_json("review_suggestions", "suggestion_id", suggestion.suggestion_id, suggestion.model_dump(mode="json", by_alias=True))

    def persist_verification(self, verification: FullNoteVerification) -> None:
        super().persist_verification(verification)
        self._persist_json("review_verifications", "verification_id", verification.full_verification_id, verification.model_dump(mode="json", by_alias=True))

    def persist_claim_feedback(self, feedback: ClaimReverificationResponse) -> None:
        super().persist_claim_feedback(feedback)
        self._persist_json("review_claim_feedback", "feedback_id", feedback.review_verification_id, feedback.model_dump(mode="json", by_alias=True))

    def persist_disposition(self, disposition: NoteDisposition) -> None:
        super().persist_disposition(disposition)
        self._persist_json("review_dispositions", "disposition_id", disposition.disposition_id, disposition.model_dump(mode="json", by_alias=True))

    def append_event(self, event: AuditEvent) -> AuditEvent:
        saved = super().append_event(event)
        try:
            with self._database.transaction() as connection:
                connection.execute(
                    "INSERT INTO review_audit_events(event_id, note_id, sequence, payload_json) VALUES (%s, %s, %s, %s)",
                    (event.event_id, event.note_id, event.sequence, Jsonb(event.model_dump(mode="json", by_alias=True))),
                )
        except UniqueViolation as error:
            self.events[event.note_id].pop()
            raise ReviewRepositoryError("AUDIT_EVENT_CONFLICT") from error
        return saved

    def bind_idempotency(self, operation: str, key: str, digest: str) -> None:
        super().bind_idempotency(operation, key, digest)
        try:
            with self._database.transaction() as connection:
                connection.execute("INSERT INTO review_idempotency(operation, key, digest) VALUES (%s, %s, %s)", (operation, key, digest))
        except UniqueViolation:
            with self._database.transaction() as connection:
                existing = connection.execute("SELECT digest FROM review_idempotency WHERE operation = %s AND key = %s", (operation, key)).fetchone()
                if existing is None or existing["digest"] != digest:
                    raise ReviewRepositoryError("IDEMPOTENCY_KEY_CONFLICT")

    def close(self) -> None:
        return None


class PostgresEvaluationRepository:
    def __init__(self, database_url: str) -> None:
        self._database = _PostgresDatabase(database_url)

    def save_dataset(self, dataset: BenchmarkDataset) -> BenchmarkDataset:
        payload = dataset.model_dump(mode="json", by_alias=True)
        with self._database.transaction() as connection:
            row = connection.execute("SELECT payload_json FROM evaluation_datasets WHERE dataset_id = %s AND dataset_version = %s", (dataset.dataset_id, dataset.dataset_version)).fetchone()
            if row is not None and row["payload_json"] != payload:
                raise EvaluationRepositoryError("dataset version is immutable")
            if row is None:
                connection.execute("INSERT INTO evaluation_datasets(dataset_id, dataset_version, content_hash, payload_json) VALUES (%s, %s, %s, %s)", (dataset.dataset_id, dataset.dataset_version, dataset.content_hash, Jsonb(payload)))
        return dataset

    def get_dataset(self, dataset_id: str, dataset_version: str) -> BenchmarkDataset | None:
        with self._database.transaction() as connection:
            row = connection.execute("SELECT payload_json FROM evaluation_datasets WHERE dataset_id = %s AND dataset_version = %s", (dataset_id, dataset_version)).fetchone()
            return BenchmarkDataset.model_validate(row["payload_json"]) if row else None

    def reserve(self, idempotency_key: str, input_digest: str, run_id: str) -> bool:
        with self._database.transaction() as connection:
            row = connection.execute("SELECT input_digest FROM evaluation_idempotency WHERE idempotency_key = %s FOR UPDATE", (idempotency_key,)).fetchone()
            if row:
                if row["input_digest"] != input_digest:
                    raise IdempotencyConflict("idempotency key is bound to a different request")
                return False
            try:
                connection.execute("INSERT INTO evaluation_idempotency(idempotency_key, input_digest, evaluation_run_id) VALUES (%s, %s, %s)", (idempotency_key, input_digest, run_id))
            except UniqueViolation as error:
                raise IdempotencyConflict("evaluation idempotency reservation conflicted") from error
            return True

    def save_run(self, run: EvaluationRun) -> EvaluationRun:
        payload = run.model_dump(mode="json", by_alias=True)
        with self._database.transaction() as connection:
            row = connection.execute("SELECT payload_json FROM evaluation_runs WHERE evaluation_run_id = %s", (run.evaluation_run_id,)).fetchone()
            if row is not None and row["payload_json"] != payload:
                raise EvaluationRepositoryError("terminal evaluation run is immutable")
            if row is None:
                connection.execute("INSERT INTO evaluation_runs(evaluation_run_id, payload_json, created_at) VALUES (%s, %s, %s)", (run.evaluation_run_id, Jsonb(payload), run.started_at))
        return run

    def get_run(self, run_id: str) -> EvaluationRun | None:
        with self._database.transaction() as connection:
            row = connection.execute("SELECT payload_json FROM evaluation_runs WHERE evaluation_run_id = %s", (run_id,)).fetchone()
            return EvaluationRun.model_validate(row["payload_json"]) if row else None

    def run_id_for_idempotency(self, idempotency_key: str) -> str | None:
        with self._database.transaction() as connection:
            row = connection.execute("SELECT evaluation_run_id FROM evaluation_idempotency WHERE idempotency_key = %s", (idempotency_key,)).fetchone()
            return row["evaluation_run_id"] if row else None

    def list_runs(self) -> tuple[EvaluationRun, ...]:
        with self._database.transaction() as connection:
            rows = connection.execute("SELECT payload_json FROM evaluation_runs ORDER BY created_at, evaluation_run_id").fetchall()
            return tuple(EvaluationRun.model_validate(row["payload_json"]) for row in rows)

    def close(self) -> None:
        return None


@dataclass
class PostgresPersistence:
    source: PostgresSourceRepository
    notes: PostgresNoteRepository
    review: PostgresReviewRepository
    evaluation: PostgresEvaluationRepository

    def check(self) -> bool:
        return self.source._database.check()


def create_postgres_persistence(database_url: str) -> PostgresPersistence:
    run_migrations(database_url)
    return PostgresPersistence(
        source=PostgresSourceRepository(database_url),
        notes=PostgresNoteRepository(database_url),
        review=PostgresReviewRepository(database_url),
        evaluation=PostgresEvaluationRepository(database_url),
    )
