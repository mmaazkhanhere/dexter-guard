from datetime import datetime, timezone

from nursing_notes.contracts import NoteRevisionRecord
from nursing_notes.repository import InMemoryNoteRepository
from source_ingestion.contracts import SourceDocument
from source_ingestion.repository import InMemorySourceRepository
from source_ingestion.service import SourceIngestionService

from claim_extraction.revision_reader import NursingNoteRevisionReader


def test_revision_reader_adapts_existing_note_identity_and_carries_source_metadata() -> None:
    source_repository = InMemorySourceRepository()
    source_service = SourceIngestionService(
        source_repository,
        id_factory=lambda: "source-1",
        clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    source = source_service.create_source(
        {"resident_test_id": "resident-1", "language": "de-DE", "transcript_text": "synthetic source"}
    )
    note_repository = InMemoryNoteRepository()
    note_repository.create(
        NoteRevisionRecord(
            noteId="note-1",
            revision=1,
            content="Bewohnerin ist wach.",
            status="DRAFT",
            origin="IMPORTED",
            sourceId=source.source_id,
            sourceVersion=source.source_version,
            validationRunId="validation-1",
            facts=(),
            schemaVersion="nursing-fact-v1",
            rulesetVersion="import-no-inference-v1",
            sourceTextHash="b" * 64,
            normalizationPolicy="unicode-code-point-v1",
            createdAt=datetime(2026, 1, 1, tzinfo=timezone.utc),
            createdBy="synthetic-test",
            externalOrigin={"system": "fixture", "externalNoteId": "note-1"},
        )
    )
    # The note repository record uses the source hash field as its existing
    # provenance contract; this fixture intentionally corrects it to the actual
    # source hash before exercising the adapter.
    record = note_repository.get("note-1", 1)
    corrected = record.model_copy(update={"source_text_hash": __import__("hashlib").sha256(source.transcript_text.encode()).hexdigest()})
    note_repository._revisions[("note-1", 1)] = corrected  # noqa: SLF001 - fixture-only adapter setup

    context = NursingNoteRevisionReader(note_repository, source_service).read("note-1:r1")
    assert context.note_revision_id == "note-1:r1"
    assert context.resident_test_id == "resident-1"
    assert context.source_reference.source_id == "source-1"
