from __future__ import annotations

import json

import pytest


def test_valid_german_transcript_is_accepted_and_round_trips_exactly(client, valid_payload, repository):
    response = client.post("/sources", json=valid_payload)

    assert response.status_code == 201
    created = response.json()
    assert created["source_id"]
    assert created["source_version"] == 1
    assert created["resident_test_id"] == "resident-test-001"
    assert created["language"] == "de-DE"
    assert created["transcript_text"] == valid_payload["transcript_text"]
    assert repository.count() == 1

    retrieved = client.get(f"/sources/{created['source_id']}/versions/1")
    assert retrieved.status_code == 200
    assert retrieved.json() == created


@pytest.mark.parametrize("text", ["", " ", "\t\r\n"])
def test_blank_transcript_is_rejected_without_persistence(client, valid_payload, repository, text):
    payload = {**valid_payload, "transcript_text": text}

    response = client.post("/sources", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_TRANSCRIPT"
    assert response.json()["field"] == "transcript_text"
    assert repository.count() == 0


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("transcript_text", 123, "INVALID_TRANSCRIPT"),
        ("transcript_text", ["text"], "INVALID_TRANSCRIPT"),
        ("resident_test_id", ["resident-1", "resident-2"], "INVALID_RESIDENT_TEST_ID"),
        ("resident_test_id", "", "INVALID_RESIDENT_TEST_ID"),
        ("resident_test_id", "resident with spaces", "INVALID_RESIDENT_TEST_ID"),
        ("language", "en-US", "INVALID_REQUEST"),
    ],
)
def test_structurally_invalid_payloads_return_stable_errors(
    client, valid_payload, repository, field, value, code
):
    payload = {**valid_payload, field: value}

    response = client.post("/sources", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == code
    assert response.json()["message"]
    assert repository.count() == 0


def test_missing_and_extra_fields_are_rejected_without_partial_persistence(client, valid_payload, repository):
    missing = {key: value for key, value in valid_payload.items() if key != "transcript_text"}
    extra = {**valid_payload, "unexpected": True}

    missing_response = client.post("/sources", json=missing)
    extra_response = client.post("/sources", json=extra)

    assert missing_response.status_code == 400
    assert extra_response.status_code == 400
    assert missing_response.json()["code"] == "INVALID_TRANSCRIPT"
    assert extra_response.json()["code"] == "INVALID_REQUEST"
    assert repository.count() == 0


def test_duplicate_resident_field_is_rejected(client, valid_payload, repository):
    raw = json.dumps(
        {
            "resident_test_id": "resident-test-001",
            "language": "de-DE",
            "transcript_text": valid_payload["transcript_text"],
        }
    ).replace(
        '"resident_test_id": "resident-test-001"',
        '"resident_test_id": "resident-test-001", "resident_test_id": "resident-test-002"',
    )

    response = client.post("/sources", content=raw, headers={"content-type": "application/json"})

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_RESIDENT_TEST_ID"
    assert repository.count() == 0


def test_audio_and_non_json_inputs_are_not_supported(client, valid_payload, repository):
    audio_response = client.post("/sources", json={"audio": "synthetic-audio-bytes"})
    content_response = client.post(
        "/sources",
        content=b"synthetic-audio",
        headers={"content-type": "audio/wav"},
    )

    assert audio_response.status_code == 415
    assert audio_response.json()["code"] == "UNSUPPORTED_INPUT_TYPE"
    assert content_response.status_code == 415
    assert content_response.json()["code"] == "UNSUPPORTED_INPUT_TYPE"
    assert repository.count() == 0


def test_non_object_and_malformed_json_are_structured_errors(client, repository):
    non_object = client.post("/sources", json=["not", "an", "object"])
    malformed = client.post(
        "/sources",
        content=b'{"resident_test_id":',
        headers={"content-type": "application/json"},
    )

    assert non_object.status_code == 400
    assert malformed.status_code == 400
    assert non_object.json()["code"] == "INVALID_REQUEST"
    assert malformed.json()["code"] == "INVALID_REQUEST"
    assert repository.count() == 0


def test_each_accepted_submission_gets_a_unique_source_id(client, valid_payload):
    first = client.post("/sources", json=valid_payload)
    second = client.post("/sources", json=valid_payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["source_id"] != second.json()["source_id"]


def test_exact_text_preserves_diacritics_combining_marks_whitespace_and_line_endings(client):
    text = "Ärztin: müde e\u0301.\r\n  Zeile zwei — bleibt exakt.  "
    payload = {
        "resident_test_id": "synthetic-001",
        "language": "de-DE",
        "transcript_text": text,
    }

    created = client.post("/sources", json=payload).json()
    retrieved = client.get(f"/sources/{created['source_id']}/versions/1").json()

    assert retrieved["transcript_text"] == text
