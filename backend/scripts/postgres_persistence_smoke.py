"""Run a safe synthetic PostgreSQL persistence round-trip.

Usage: uv run python backend/scripts/postgres_persistence_smoke.py

The script loads DATABASE_URL from backend/.env for local verification, creates
only uniquely-prefixed synthetic records, verifies them after reopening each
repository, and removes only those records in a final transaction.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from uuid import uuid4

from dotenv import load_dotenv

from app.postgres import (
    PostgresNoteRepository,
    PostgresReviewRepository,
    PostgresSourceRepository,
    create_postgres_persistence,
)
import psycopg
from psycopg.rows import dict_row

from human_review.service import ReviewService
from source_ingestion.contracts import SourceDocument


def main() -> None:
    load_dotenv("backend/.env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is not configured")

    persistence = create_postgres_persistence(database_url)
    token = uuid4().hex
    source_id = f"postgres-smoke-source-{token}"
    note_id = f"postgres-smoke-note-{token}"
    created_at = datetime.now(timezone.utc)
    try:
        source = SourceDocument(
            source_id=source_id,
            source_version=1,
            resident_test_id=f"synthetic-{token[:12]}",
            language="de-DE",
            transcript_text="Die Bewohnerin berichtet über leichte Schmerzen am linken Knie.",
            created_at=created_at,
        )
        persistence.source.create_initial(source)
        persisted_source = PostgresSourceRepository(database_url).get(source_id, 1)
        assert persisted_source.transcript_text == source.transcript_text

        revision = persistence.notes
        from nursing_notes.contracts import NoteRevisionRecord

        revision.create(NoteRevisionRecord(
            noteId=note_id,
            revision=1,
            previousRevisionId=None,
            content="Bewohnerin berichtet über leichte Schmerzen am linken Knie.",
            status="DRAFT",
            origin="IMPORTED",
            sourceId=source_id,
            sourceVersion=1,
            externalOrigin={"system": "postgres-smoke", "externalNoteId": token},
            validationRunId=f"validation-{token}",
            facts=(),
            generationRunId=None,
            modelId=None,
            promptVersion=None,
            schemaVersion="smoke-v1",
            rulesetVersion="smoke-v1",
            sourceTextHash="synthetic-hash",
            normalizationPolicy="NFC",
            createdAt=created_at,
            createdBy="postgres-smoke",
        ))
        reopened_notes = PostgresNoteRepository(database_url)
        assert reopened_notes.get(note_id, 1).content.startswith("Bewohnerin")

        review = ReviewService(repository=persistence.review)
        review.seed_note(note_id, source_id, 1, "Bewohnerin berichtet über leichte Schmerzen am linken Knie.")
        reopened_review = PostgresReviewRepository(database_url)
        assert reopened_review.get_replay("missing", "missing") is None
        assert reopened_review.latest[note_id] == 1
        assert len(reopened_review.audit(note_id)) == 1
        print(f"POSTGRES_SMOKE_OK source={source_id} note={note_id}")
    finally:
        with psycopg.connect(database_url, row_factory=dict_row) as connection:
            with connection.transaction():
                connection.execute("DELETE FROM review_audit_events WHERE note_id = %s", (note_id,))
                connection.execute("DELETE FROM review_notes WHERE note_key LIKE %s", (f"{note_id}:%",))
                connection.execute("DELETE FROM nursing_facts WHERE note_id = %s", (note_id,))
                connection.execute("DELETE FROM note_revisions WHERE note_id = %s", (note_id,))
                connection.execute("DELETE FROM source_documents WHERE source_id = %s", (source_id,))
        for repository in (persistence.source, persistence.notes, persistence.review, persistence.evaluation):
            repository.close()


if __name__ == "__main__":
    main()
