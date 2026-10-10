"""Adapters that expose immutable Spec 002 note revisions to Spec 003."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from .models import EvidenceSourceReference


NOTE_REVISION_PATTERN = re.compile(r"^(?P<note_id>.+):r(?P<revision>[1-9][0-9]*)$")


class RevisionReaderError(LookupError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class NoteRevisionContext:
    note_revision_id: str
    note_body: str
    note_body_hash: str
    resident_test_id: str
    language: str
    synthetic: bool
    source_reference: EvidenceSourceReference


class NursingNoteRevisionReader:
    """Resolve ``note-id:rN`` to one immutable note and its source metadata."""

    def __init__(self, note_repository: Any, source_service: Any) -> None:
        self.note_repository = note_repository
        self.source_service = source_service

    def read(self, note_revision_id: str) -> NoteRevisionContext:
        match = NOTE_REVISION_PATTERN.fullmatch(note_revision_id)
        if match is None:
            raise RevisionReaderError("REVISION_NOT_FOUND", "The note revision identifier is invalid.")
        note_id = match.group("note_id")
        revision = int(match.group("revision"))
        try:
            record = self.note_repository.get(note_id, revision)
        except Exception as error:
            raise RevisionReaderError("REVISION_NOT_FOUND", "The requested note revision does not exist.") from error

        try:
            source = self.source_service.get_source_version(record.source_id, record.source_version)
        except Exception as error:
            raise RevisionReaderError("REVISION_MISMATCH", "The note's immutable source reference is unavailable.") from error

        note_body_hash = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        source_text_hash = hashlib.sha256(source.transcript_text.encode("utf-8")).hexdigest()
        if record.source_text_hash != source_text_hash:
            raise RevisionReaderError("REVISION_MISMATCH", "The note's source provenance does not match the source record.")
        if not getattr(source, "resident_test_id", None):
            raise RevisionReaderError("NON_SYNTHETIC_INPUT", "The note has no synthetic resident association.")
        if not record.content or not record.content.strip():
            raise RevisionReaderError("REVISION_MISMATCH", "The stored note revision has no usable body.")

        return NoteRevisionContext(
            note_revision_id=f"{record.note_id}:r{record.revision}",
            note_body=record.content,
            note_body_hash=note_body_hash,
            resident_test_id=source.resident_test_id,
            language=source.language,
            synthetic=True,
            source_reference=EvidenceSourceReference(
                sourceId=source.source_id,
                sourceVersion=source.source_version,
                sourceTextHash=source_text_hash,
                normalizationPolicy=record.normalization_policy,
            ),
        )
