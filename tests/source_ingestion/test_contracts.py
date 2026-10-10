from __future__ import annotations

from pathlib import Path

import yaml

from source_ingestion.contracts import SourceDocument, SourceSpan


def test_downstream_consumers_can_import_and_construct_source_contracts():
    document = SourceDocument(
        source_id="source-001",
        source_version=1,
        resident_test_id="resident-001",
        language="de-DE",
        transcript_text="Beobachtung.",
        created_at="2026-10-10T00:00:00Z",
    )
    span = SourceSpan(source_id=document.source_id, source_version=1, start=0, end=11)

    assert document.source_id == span.source_id
    assert document.source_version == span.source_version
    assert document.transcript_text[span.start : span.end] == "Beobachtung"


def test_openapi_contract_matches_runtime_source_document_and_span_contracts():
    contract_path = Path(__file__).parents[2] / "specs" / "001-source-and-note-ingestion" / "contracts" / "source-api.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    schemas = contract["components"]["schemas"]

    assert schemas["SourceDocument"]["required"] == [
        "source_id",
        "source_version",
        "resident_test_id",
        "language",
        "transcript_text",
        "created_at",
    ]
    assert schemas["SourceSpan"]["required"] == ["source_id", "source_version", "start", "end"]
    assert schemas["Language"]["enum"] == ["de-DE"]
    assert schemas["SourceSpan"]["properties"]["start"]["minimum"] == 0
    assert schemas["SourceSpan"]["properties"]["end"]["minimum"] == 1
    assert "/sources" in contract["paths"]
    assert "/sources/{source_id}/versions" in contract["paths"]
    assert "/sources/{source_id}/versions/{source_version}" in contract["paths"]
    assert "/source-spans/resolve" in contract["paths"]


def test_feature_modules_do_not_require_an_llm_provider():
    import source_ingestion

    assert not any(name in source_ingestion.__dict__ for name in ("openai", "anthropic", "llama_index"))
