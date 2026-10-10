from __future__ import annotations

import pytest


def _payload(text: str) -> dict[str, str]:
    return {
        "resident_test_id": "resident-001",
        "language": "de-DE",
        "transcript_text": text,
    }


def test_valid_span_uses_unicode_scalar_value_half_open_offsets(client):
    text = "Ä😀e\u0301\r\n"
    source = client.post("/sources", json=_payload(text)).json()

    response = client.post(
        "/source-spans/resolve",
        json={
            "source_id": source["source_id"],
            "source_version": 1,
            "start": 1,
            "end": 4,
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "😀e\u0301"
    assert len(text) == 6  # Ä, 😀, e, combining mark, CR, LF
    assert response.json()["start"] == 1
    assert response.json()["end"] == 4


@pytest.mark.parametrize(
    ("start", "end"),
    [(-1, 1), (0, 0), (2, 2), (3, 2), (0, 7), (6, 7)],
)
def test_invalid_span_boundaries_are_rejected(client, start, end):
    source = client.post("/sources", json=_payload("Ä😀e\u0301\r\n")).json()
    response = client.post(
        "/source-spans/resolve",
        json={
            "source_id": source["source_id"],
            "source_version": 1,
            "start": start,
            "end": end,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SOURCE_SPAN"


def test_missing_source_and_version_span_references_are_rejected(client):
    missing_source = client.post(
        "/source-spans/resolve",
        json={"source_id": "missing", "source_version": 1, "start": 0, "end": 1},
    )
    source = client.post("/sources", json=_payload("Text.")).json()
    missing_version = client.post(
        "/source-spans/resolve",
        json={"source_id": source["source_id"], "source_version": 2, "start": 0, "end": 1},
    )

    assert missing_source.status_code == 404
    assert missing_source.json()["code"] == "SOURCE_NOT_FOUND"
    assert missing_version.status_code == 404
    assert missing_version.json()["code"] == "SOURCE_VERSION_NOT_FOUND"


def test_span_is_bound_to_referenced_version_and_never_redirected(client):
    first = client.post("/sources", json=_payload("Long version one.")).json()
    client.post(
        f"/sources/{first['source_id']}/versions",
        json={"expected_source_version": 1, "transcript_text": "Short."},
    )

    response = client.post(
        "/source-spans/resolve",
        json={"source_id": first["source_id"], "source_version": 2, "start": 0, "end": 12},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SOURCE_SPAN"


def test_span_payload_types_and_extra_fields_are_rejected(client):
    source = client.post("/sources", json=_payload("Text.")).json()
    response = client.post(
        "/source-spans/resolve",
        json={
            "source_id": source["source_id"],
            "source_version": "1",
            "start": 0,
            "end": 1,
            "excerpt": "Text.",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SOURCE_SPAN"
