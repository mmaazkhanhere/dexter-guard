from __future__ import annotations

from nursing_notes.adapters import DeterministicNursingNoteAdapter
from nursing_notes.contracts import GenerationResult
from nursing_notes.errors import NoteError, NoteErrorCode
from nursing_notes.repository import InMemoryNoteRepository
from nursing_notes.service import NursingNoteService
from source_ingestion.app import create_app
from source_ingestion.repository import InMemorySourceRepository
from source_ingestion.service import SourceIngestionService
from fastapi.testclient import TestClient

from .conftest import create_source, fact, result_factory


def test_gen_001_valid_german_transcript_returns_editable_professional_draft(note_context):
    client = note_context["client"]
    source = create_source(client, "Frau Müller berichtet über unruhigen Schlaf.")
    adapter = DeterministicNursingNoteAdapter()
    note_service = NursingNoteService(
        note_context["source_service"],
        repository=note_context["note_repository"],
        generation_adapter=adapter,
    )
    client = TestClient(create_app(note_context["source_service"], note_service))

    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "synthetic-tester"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "Pflegedokumentation" in body["content"]
    assert body["origin"] == "GENERATED"
    assert body["status"] == "DRAFT"
    assert body["sourceId"] == source["source_id"]
    assert body["sourceVersion"] == 1
    assert body["revision"] == 1
    assert body["facts"]


def test_gen_002_preserves_numeric_values_and_units_and_rejects_changes(note_context):
    client = note_context["client"]
    text = "Die Temperatur beträgt 37,5 °C."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    good = fact(
        source_model,
        text,
        fact_type="MEASUREMENT",
        numericValue="37,5",
        unit="°C",
    )
    note_context["adapter"].factory = result_factory(good)
    accepted = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert accepted.status_code == 201
    assert accepted.json()["facts"][0]["numericValue"] == "37,5"
    assert accepted.json()["facts"][0]["unit"] == "°C"

    changed = fact(source_model, text, fact_type="MEASUREMENT", numericValue="38,5", unit="°C")
    note_context["adapter"].factory = result_factory(changed)
    rejected = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "GENERATION_REJECTED"
    assert note_context["note_repository"].count() == 1

    changed_unit = fact(source_model, text, fact_type="MEASUREMENT", numericValue="37,5", unit="°F")
    note_context["adapter"].factory = result_factory(changed_unit)
    rejected_unit = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert rejected_unit.status_code == 422
    assert rejected_unit.json()["code"] == "GENERATION_REJECTED"
    assert note_context["note_repository"].count() == 1


def test_bidirectional_fixture_rejects_material_source_span_omission(note_context):
    client = note_context["client"]
    text = "Die Bewohnerin ruht. Die Haut ist trocken."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    omitted = fact(source_model, "Die Bewohnerin ruht.")
    note_context["adapter"].factory = result_factory(omitted)

    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "GENERATION_REJECTED"
    assert note_context["note_repository"].count() == 0


def test_bidirectional_fixture_rejects_draft_to_source_mismatch(note_context):
    client = note_context["client"]
    text = "Die Bewohnerin berichtet über Schwindel."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    candidate = fact(source_model, text)
    note_context["adapter"].factory = result_factory(candidate, content="Pflegedokumentation: Schmerzen.")

    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "GENERATION_REJECTED"
    assert note_context["note_repository"].count() == 0


def test_gen_003_negation_is_not_reversed(note_context):
    client = note_context["client"]
    text = "Die Bewohnerin verneint Schmerzen."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    candidate = fact(source_model, text, fact_type="SYMPTOM", polarity="NEGATED")
    note_context["adapter"].factory = result_factory(candidate)
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 201
    assert response.json()["facts"][0]["polarity"] == "NEGATED"

    reversed_fact = fact(source_model, text, fact_type="SYMPTOM", polarity="AFFIRMED")
    note_context["adapter"].factory = result_factory(reversed_fact)
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 422


def test_gen_004_uncertainty_is_not_converted_to_certainty(note_context):
    client = note_context["client"]
    text = "Möglicherweise besteht Schwindel."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    candidate = fact(source_model, text, fact_type="SYMPTOM", certainty="UNCERTAIN")
    note_context["adapter"].factory = result_factory(candidate)
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 201

    certain = fact(source_model, text, fact_type="SYMPTOM", certainty="CERTAIN")
    note_context["adapter"].factory = result_factory(certain)
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 422


def test_gen_005_resident_reported_information_retains_attribution(note_context):
    client = note_context["client"]
    text = "Die Bewohnerin berichtet über Übelkeit."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    candidate = fact(
        source_model,
        text,
        fact_type="SYMPTOM",
        attribution="RESIDENT_REPORTED",
    )
    note_context["adapter"].factory = result_factory(candidate)
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 201
    assert response.json()["facts"][0]["attribution"] == "RESIDENT_REPORTED"


def test_gen_006_returns_observation_symptom_measurement_and_action_facts(note_context):
    client = note_context["client"]
    text = "Die Haut ist trocken. Die Bewohnerin berichtet über Schmerz. Die Temperatur beträgt 36,8 °C. Die Pflegekraft führte eine Lagerung durch."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    candidates = (
        fact(source_model, "Die Haut ist trocken.", fact_type="OBSERVATION"),
        fact(source_model, "Die Bewohnerin berichtet über Schmerz.", fact_type="SYMPTOM", attribution="RESIDENT_REPORTED"),
        fact(
            source_model,
            "Die Temperatur beträgt 36,8 °C.",
            fact_type="MEASUREMENT",
            numericValue="36,8",
            unit="°C",
        ),
        fact(source_model, "Die Pflegekraft führte eine Lagerung durch.", fact_type="ACTION", attribution="CAREGIVER_OBSERVED"),
    )
    note_context["adapter"].factory = result_factory(*candidates)
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 201
    body = response.json()
    assert {item["type"] for item in body["facts"]} == {"OBSERVATION", "SYMPTOM", "MEASUREMENT", "ACTION"}
    assert all(item["sourceAnchor"]["sourceId"] == source["source_id"] for item in body["facts"])
    assert all(item["noteId"] == body["noteId"] and item["revision"] == 1 for item in body["facts"])


def test_gen_007_import_preserves_exact_content_and_never_calls_generation(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    external_text = "  Extern verfasste Notiz.\r\n"
    response = client.post(
        "/api/v1/notes/import",
        json={
            "sourceId": source["source_id"],
            "sourceVersion": 1,
            "content": external_text,
            "externalOrigin": {"system": "pflege-system-test", "externalNoteId": "ext-001"},
            "requestedBy": "tester",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content"] == external_text
    assert body["origin"] == "IMPORTED"
    assert body["externalOrigin"]["system"] == "pflege-system-test"
    assert body["facts"] == []
    assert note_context["adapter"].invocation_count == 0


def test_gen_008_malformed_provider_output_is_controlled_and_atomic(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    note_context["adapter"].factory = lambda _: {"content": "Notiz", "facts": [{"type": "OBSERVATION"}]}
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "GENERATION_REJECTED"
    assert note_context["note_repository"].count() == 0
    assert note_context["note_repository"].fact_count() == 0


def test_gen_009_new_notes_are_drafts_and_revision_lineage_is_explicit(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    note_context["adapter"].factory = result_factory(fact(source_model, source_model.transcript_text))
    generated = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    imported = client.post(
        "/api/v1/notes/import",
        json={
            "sourceId": source["source_id"],
            "sourceVersion": 1,
            "content": "Externe Notiz.",
            "externalOrigin": {"system": "test", "externalNoteId": "n-1"},
            "requestedBy": "tester",
        },
    )
    assert generated.json()["status"] == imported.json()["status"] == "DRAFT"
    assert "APPROVED" not in generated.json().values()
    assert "VERIFIED" not in imported.json().values()

    revision = note_context["note_service"].create_revision(
        generated.json()["noteId"],
        "Bearbeitete Notiz.",
        expected_revision=1,
        requested_by="editor-test",
    )
    assert revision.revision == 2
    assert revision.previous_revision_id == f"{generated.json()['noteId']}:r1"
    assert revision.status == "DRAFT"


def test_gen_010_unsupported_diagnosis_is_rejected(note_context):
    client = note_context["client"]
    text = "Die Bewohnerin hustet."
    source = create_source(client, text)
    source_model = note_context["source_service"].get_source_version(source["source_id"], 1)
    note_context["adapter"].factory = result_factory(
        fact(source_model, text, fact_type="SYMPTOM"),
        content="Pflegedokumentation: Diagnose Pneumonie.",
    )
    response = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "GENERATION_REJECTED"
    assert note_context["note_repository"].count() == 0


def test_missing_source_version_and_invalid_payloads_do_not_persist(note_context):
    client = note_context["client"]
    missing = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": "missing", "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "SOURCE_NOT_FOUND"

    invalid = client.post("/api/v1/notes/generate", json={"sourceId": "missing"})
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "INVALID_NOTE_REQUEST"
    assert note_context["note_repository"].count() == 0


def test_provider_failure_and_empty_output_are_controlled(note_context):
    client = note_context["client"]
    source = create_source(client, "Die Bewohnerin ruht.")
    note_context["adapter"].error = RuntimeError("synthetic provider outage")
    failed = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert failed.status_code == 422
    assert failed.json()["code"] == "GENERATION_PROVIDER_FAILURE"

    note_context["adapter"].error = None
    note_context["adapter"].factory = lambda _: {"content": "", "facts": []}
    empty = client.post(
        "/api/v1/notes/generate",
        json={"sourceId": source["source_id"], "sourceVersion": 1, "requestedBy": "tester"},
    )
    assert empty.status_code == 422
    assert note_context["note_repository"].count() == 0
