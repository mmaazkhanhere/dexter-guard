from __future__ import annotations

import time

from fastapi.testclient import TestClient

from nursing_notes.contracts import GenerationResult
from nursing_notes.observability import GenerationMetrics
from nursing_notes.service import NursingNoteService
from source_ingestion.app import create_app

from .conftest import create_source, fact, result_factory


def _generate_client(note_context, adapter, *, timeout: float, attempts: int, metrics: GenerationMetrics):
    service = NursingNoteService(
        note_context["source_service"],
        repository=note_context["note_repository"],
        generation_adapter=adapter,
        provider_timeout_seconds=timeout,
        max_provider_attempts=attempts,
        metrics=metrics,
    )
    return TestClient(create_app(note_context["source_service"], service))


class RetryingAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.run_ids: list[str | None] = []

    def generate(self, source, *, generation_run_id=None):
        self.calls += 1
        self.run_ids.append(generation_run_id)
        if self.calls == 1:
            raise RuntimeError("synthetic transient failure")
        return GenerationResult(
            content="Pflegedokumentation: Bewohnerin ruht.",
            facts=(fact(source, source.transcript_text),),
            modelId="synthetic-model",
            promptVersion="prompt-v1",
            schemaVersion="nursing-fact-v1",
            rulesetVersion="generation-guardrails-v1",
        )


class SlowAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, source, *, generation_run_id=None):
        self.calls += 1
        time.sleep(0.05)
        return GenerationResult(
            content="Pflegedokumentation: Bewohnerin ruht.",
            facts=(fact(source, source.transcript_text),),
        )


def test_retry_is_bounded_and_reuses_one_idempotent_generation_run_id(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    metrics = GenerationMetrics()
    adapter = RetryingAdapter()
    client = _generate_client(note_context, adapter, timeout=0.2, attempts=2, metrics=metrics)

    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )

    assert response.status_code == 201
    assert adapter.calls == 2
    assert len(set(adapter.run_ids)) == 1
    assert response.json()["generationRunId"] == adapter.run_ids[0]
    snapshot = metrics.snapshot()
    assert snapshot.provider_attempts == 2
    assert snapshot.provider_failures == 0
    assert snapshot.successful_generations == 1


def test_provider_timeout_is_controlled_and_does_not_persist(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    metrics = GenerationMetrics()
    adapter = SlowAdapter()
    client = _generate_client(note_context, adapter, timeout=0.001, attempts=2, metrics=metrics)

    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "GENERATION_PROVIDER_TIMEOUT"
    assert adapter.calls == 1
    assert note_context["note_repository"].count() == 0
    snapshot = metrics.snapshot()
    assert snapshot.provider_attempts == 1
    assert snapshot.provider_failures == 1


def test_rejection_metrics_are_content_free_and_imports_have_no_provider_attempt(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    metrics = GenerationMetrics()
    adapter = type("RejectingAdapter", (), {"generate": lambda self, source: {"content": "Notiz", "facts": []}})()
    client = _generate_client(note_context, adapter, timeout=0.2, attempts=1, metrics=metrics)

    rejected = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    imported = client.post(
        "/api/v1/notes/import",
        json={
            "sourceId": source["source_id"],
            "sourceVersion": 1,
            "content": "Externe Notiz.",
            "externalOrigin": {"system": "synthetic", "externalNoteId": "ext-1"},
            "requestedBy": "tester",
        },
    )

    assert rejected.status_code == 422
    assert imported.status_code == 201
    snapshot = metrics.snapshot()
    assert snapshot.provider_attempts == 1
    assert snapshot.generation_rejections == 1
    assert snapshot.imports == 1
    assert source_model.transcript_text not in repr(snapshot)
    assert "resident-test-002" not in repr(snapshot)
