from types import SimpleNamespace

import pytest

from app.workflow import OfflineSemanticEvidenceProvider


def _claim(identifier: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=identifier, claim_text=text)


@pytest.mark.parametrize(
    ("transcript", "claim", "expected_status", "expected_discrepancy"),
    [
        ("Frau Müller verneint Schmerzen.", "Frau Müller hat keine Schmerzen.", "SUPPORTED", None),
        ("Frau Müller verneint Schmerzen.", "Frau Müller klagt über Schmerzen.", "CONTRADICTED", "NEGATION"),
        ("Frau Müller berichtet möglicherweise Schmerzen.", "Frau Müller klagt über Schmerzen.", "UNCERTAIN", "CERTAINTY"),
        ("Frau Müller schläft ruhig.", "Frau Müller hat Fieber.", "UNSUPPORTED", None),
    ],
)
def test_offline_fallback_compares_german_meaning_without_literal_sentence_matching(
    transcript: str,
    claim: str,
    expected_status: str,
    expected_discrepancy: str | None,
) -> None:
    provider = OfflineSemanticEvidenceProvider()

    result = provider.verify(
        claims=(_claim("claim-1", claim),),
        source_text=transcript,
        run_id="run-1",
        source_id="source-1",
        source_version=1,
    )

    finding = result["findings"][0]
    assert finding["status"] == expected_status
    if expected_status == "UNSUPPORTED":
        assert finding["sourceSpans"] == []
    else:
        assert finding["sourceSpans"]
    if expected_discrepancy is not None:
        assert expected_discrepancy in finding["discrepancies"]


def test_offline_fallback_compares_negation_within_the_matching_fact_scope() -> None:
    provider = OfflineSemanticEvidenceProvider()

    result = provider.verify(
        claims=(_claim("claim-pain", "Frau Müller hat Schmerzen."),),
        source_text="Frau Müller hat Schmerzen und keine Übelkeit.",
        run_id="run-scope",
        source_id="source-1",
        source_version=1,
    )

    finding = result["findings"][0]
    assert finding["status"] == "SUPPORTED"
    assert finding["discrepancies"] == []
    assert finding["sourceSpans"][0]["start"] == 0
    assert "Schmerzen" in "Frau Müller hat Schmerzen und keine Übelkeit."[finding["sourceSpans"][0]["start"]:finding["sourceSpans"][0]["end"]]
@pytest.mark.parametrize(
    ("claim", "expected_status", "expected_discrepancy"),
    [
        ("Frau Müller hat Schmerzen.", "SUPPORTED", None),
        ("Frau Müller hat Übelkeit.", "CONTRADICTED", "NEGATION"),
        ("Frau Müller klagt über Schmerzen.", "SUPPORTED", None),
        ("Frau Müller hat keine Übelkeit.", "SUPPORTED", None),
    ],
)
def test_mixed_positive_and_negative_symptoms_keep_negation_local(
    claim: str, expected_status: str, expected_discrepancy: str | None
) -> None:
    provider = OfflineSemanticEvidenceProvider()
    result = provider.verify(
        claims=(_claim("claim-mixed", claim),),
        source_text="Frau Müller hat Schmerzen, aber keine Übelkeit.",
        run_id="run-mixed",
        source_id="source-1",
        source_version=1,
    )
    finding = result["findings"][0]
    assert finding["status"] == expected_status
    if expected_discrepancy is not None:
        assert expected_discrepancy in finding["discrepancies"]
