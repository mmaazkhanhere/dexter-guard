from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from source_ingestion.errors import SourceError


def _create_source(client, valid_payload):
    response = client.post("/sources", json=valid_payload)
    assert response.status_code == 201
    return response.json()


def test_revision_creates_next_version_and_preserves_history(client, valid_payload):
    initial = _create_source(client, valid_payload)
    revised_text = valid_payload["transcript_text"] + "\r\nNeue Beobachtung."

    revised = client.post(
        f"/sources/{initial['source_id']}/versions",
        json={"expected_source_version": 1, "transcript_text": revised_text},
    )

    assert revised.status_code == 201
    assert revised.json()["source_version"] == 2
    assert revised.json()["resident_test_id"] == initial["resident_test_id"]
    assert revised.json()["language"] == initial["language"]
    assert client.get(f"/sources/{initial['source_id']}/versions/1").json() == initial
    assert client.get(f"/sources/{initial['source_id']}/versions/2").json()["transcript_text"] == revised_text


def test_stale_revision_returns_conflict_and_persists_nothing(client, valid_payload):
    initial = _create_source(client, valid_payload)
    created = client.post(
        f"/sources/{initial['source_id']}/versions",
        json={"expected_source_version": 1, "transcript_text": "Erste Revision."},
    )
    stale = client.post(
        f"/sources/{initial['source_id']}/versions",
        json={"expected_source_version": 1, "transcript_text": "Stale Revision."},
    )

    assert created.status_code == 201
    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_CONFLICT"
    assert client.get(f"/sources/{initial['source_id']}/versions/2").json()["transcript_text"] == "Erste Revision."
    assert client.get(f"/sources/{initial['source_id']}/versions/3").status_code == 404


def test_concurrent_revisions_have_one_winner(service, valid_payload):
    initial = service.create_source(valid_payload)

    def revise(text: str):
        try:
            return ("success", service.create_source_version(
                initial.source_id,
                {"expected_source_version": 1, "transcript_text": text},
            ))
        except SourceError as error:
            return (error.code.value, error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(revise, ["Revision A.", "Revision B."]))

    assert sum(result[0] == "success" for result in results) == 1
    assert sum(result[0] == "VERSION_CONFLICT" for result in results) == 1
    assert service.repository.count() == 2


def test_missing_source_and_version_are_distinguished(client):
    missing_source = client.get("/sources/missing-source/versions/1")
    initial_payload = {
        "resident_test_id": "resident-001",
        "language": "de-DE",
        "transcript_text": "Text.",
    }
    source = client.post("/sources", json=initial_payload).json()
    missing_version = client.get(f"/sources/{source['source_id']}/versions/2")

    assert missing_source.status_code == 404
    assert missing_source.json()["code"] == "SOURCE_NOT_FOUND"
    assert missing_version.status_code == 404
    assert missing_version.json()["code"] == "SOURCE_VERSION_NOT_FOUND"


def test_revision_cannot_change_inherited_contract_fields(client, valid_payload):
    initial = _create_source(client, valid_payload)
    response = client.post(
        f"/sources/{initial['source_id']}/versions",
        json={
            "expected_source_version": 1,
            "transcript_text": "Revision.",
            "resident_test_id": "other-resident",
            "language": "de-DE",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"
    assert client.get(f"/sources/{initial['source_id']}/versions/2").status_code == 404
