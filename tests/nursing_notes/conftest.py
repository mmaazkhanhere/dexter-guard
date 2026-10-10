from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from nursing_notes.contracts import GenerationResult
from nursing_notes.repository import InMemoryNoteRepository
from nursing_notes.service import NursingNoteService
from source_ingestion.app import create_app
from source_ingestion.repository import InMemorySourceRepository
from source_ingestion.service import SourceIngestionService


class CapturingAdapter:
    def __init__(self, factory: Callable[[object], object] | None = None, error: Exception | None = None) -> None:
        self.factory = factory
        self.error = error
        self.invocation_count = 0

    def generate(self, source):
        self.invocation_count += 1
        if self.error is not None:
            raise self.error
        assert self.factory is not None
        return self.factory(source)


@pytest.fixture
def note_context():
    source_repository = InMemorySourceRepository()
    source_service = SourceIngestionService(repository=source_repository)
    note_repository = InMemoryNoteRepository()
    adapter = CapturingAdapter()
    note_service = NursingNoteService(
        source_service,
        repository=note_repository,
        generation_adapter=adapter,
    )
    return {
        "source_repository": source_repository,
        "source_service": source_service,
        "note_repository": note_repository,
        "adapter": adapter,
        "note_service": note_service,
        "client": TestClient(create_app(source_service, note_service)),
    }


def create_source(client: TestClient, text: str) -> dict[str, object]:
    response = client.post(
        "/sources",
        json={
            "resident_test_id": "resident-test-002",
            "language": "de-DE",
            "transcript_text": text,
        },
    )
    assert response.status_code == 201
    return response.json()


def span(text: str, excerpt: str) -> dict[str, object]:
    start = text.index(excerpt)
    return {"start": start, "end": start + len(excerpt)}


def fact(source, excerpt: str, *, fact_type: str = "OBSERVATION", **values):
    return {
        "type": fact_type,
        "statement": excerpt,
        "residentSubject": source.resident_test_id,
        "sourceAnchor": {
            "sourceId": source.source_id,
            "sourceVersion": source.source_version,
            **span(source.transcript_text, excerpt),
        },
        "polarity": "AFFIRMED",
        "certainty": "CERTAIN",
        "provenance": "GENERATED_FROM_SOURCE",
        **values,
    }


def result_factory(*facts_payload, content: str | None = None):
    def factory(source):
        return GenerationResult(
            content=content or f"Pflegedokumentation:\n{source.transcript_text}",
            facts=tuple(facts_payload),
            modelId="synthetic-model",
            promptVersion="prompt-v1",
            schemaVersion="nursing-fact-v1",
            rulesetVersion="generation-guardrails-v1",
        )

    return factory
