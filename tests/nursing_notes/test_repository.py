from __future__ import annotations

from nursing_notes.adapters import DeterministicNursingNoteAdapter
from nursing_notes.repository import SQLiteNoteRepository
from nursing_notes.service import NursingNoteService
from source_ingestion.repository import InMemorySourceRepository
from source_ingestion.service import SourceIngestionService


def test_sqlite_repository_round_trips_note_revision_and_facts(tmp_path):
    source_service = SourceIngestionService(repository=InMemorySourceRepository())
    source = source_service.create_source(
        {
            "resident_test_id": "resident-test-002",
            "language": "de-DE",
            "transcript_text": "Die Bewohnerin ruht.",
        }
    )
    database_path = tmp_path / "notes.sqlite3"
    repository = SQLiteNoteRepository(database_path)
    service = NursingNoteService(
        source_service,
        repository=repository,
        generation_adapter=DeterministicNursingNoteAdapter(),
    )

    response = service.generate(
        {
            "sourceId": source.source_id,
            "sourceVersion": 1,
            "requestedBy": "synthetic-tester",
        }
    )
    repository.close()

    reopened = SQLiteNoteRepository(database_path)
    stored = reopened.get(response.note_id)
    assert stored.note_id == response.note_id
    assert stored.source_id == source.source_id
    assert stored.source_version == 1
    assert stored.status == "DRAFT"
    assert len(stored.facts) == 1
    assert reopened.count() == 1
    assert reopened.fact_count() == 1
    reopened.close()


def test_sqlite_repository_keeps_revision_history_append_only(tmp_path):
    source_service = SourceIngestionService(repository=InMemorySourceRepository())
    source = source_service.create_source(
        {
            "resident_test_id": "resident-test-002",
            "language": "de-DE",
            "transcript_text": "Die Bewohnerin ruht.",
        }
    )
    repository = SQLiteNoteRepository(tmp_path / "notes.sqlite3")
    service = NursingNoteService(
        source_service,
        repository=repository,
        generation_adapter=DeterministicNursingNoteAdapter(),
    )
    response = service.generate(
        {"sourceId": source.source_id, "sourceVersion": 1, "requestedBy": "synthetic-tester"}
    )

    revised = service.create_revision(
        response.note_id,
        "Bearbeitete Notiz.",
        expected_revision=1,
        requested_by="synthetic-editor",
    )

    assert repository.count() == 2
    assert repository.get(response.note_id, 1).content != revised.content
    assert repository.get(response.note_id).revision == 2
    assert revised.previous_revision_id == f"{response.note_id}:r1"
    repository.close()
