from __future__ import annotations

from pathlib import Path

import yaml

from nursing_notes.contracts import CandidateNursingFact


def test_notes_openapi_contract_declares_candidate_and_persisted_fact_shapes():
    contract_path = Path(__file__).parents[2] / "specs" / "002-nursing-note-generation" / "contracts" / "notes-api.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    schemas = contract["components"]["schemas"]

    assert "/api/v1/notes/generate" in contract["paths"]
    assert "/api/v1/notes/import" in contract["paths"]
    assert schemas["CandidateNursingFact"]["required"] == [
        "type",
        "statement",
        "residentSubject",
        "sourceAnchor",
        "provenance",
    ]
    assert "factId" in schemas["NursingFact"]["required"]
    assert schemas["NoteResponse"]["properties"]["status"]["const"] == "DRAFT"
    assert schemas["SourceReference"]["properties"]["sourceVersion"]["type"] == "integer"
    assert schemas["NoteResponse"]["properties"]["sourceVersion"]["type"] == "integer"
    assert "previousRevisionId" in schemas["NoteResponse"]["properties"]
    assert "ErrorResponse" in schemas
    assert len(schemas["SourceAnchor"]["oneOf"]) == 2
    assert schemas["SourceAnchor"]["oneOf"][0]["required"] == [
        "sourceId",
        "sourceVersion",
        "start",
        "end",
    ]
    assert schemas["SourceAnchor"]["oneOf"][1]["required"] == ["externalSystem", "externalFactId"]


def test_runtime_fact_contract_keeps_unknown_resident_explicit():
    fact = CandidateNursingFact(
        type="OBSERVATION",
        statement="Unklare Beobachtung.",
        residentSubject="UNKNOWN",
        sourceAnchor={"externalSystem": "synthetic-import", "externalFactId": "fact-1"},
        provenance="EXTERNALLY_SUPPLIED",
    )
    assert fact.resident_subject == "UNKNOWN"


def test_source_anchor_requires_complete_external_provenance():
    try:
        CandidateNursingFact(
            type="OBSERVATION",
            statement="Unklare Beobachtung.",
            residentSubject="UNKNOWN",
            sourceAnchor={"externalSystem": "synthetic-import"},
            provenance="EXTERNALLY_SUPPLIED",
        )
    except ValueError:
        return
    raise AssertionError("partial external provenance must be rejected")


def test_source_anchor_cannot_mix_source_span_and_external_provenance():
    try:
        CandidateNursingFact(
            type="OBSERVATION",
            statement="Unklare Beobachtung.",
            residentSubject="UNKNOWN",
            sourceAnchor={
                "sourceId": "source-1",
                "sourceVersion": 1,
                "start": 0,
                "end": 5,
                "externalSystem": "synthetic-import",
                "externalFactId": "fact-1",
            },
            provenance="EXTERNALLY_SUPPLIED",
        )
    except ValueError:
        return
    raise AssertionError("source and external provenance must be mutually exclusive")
