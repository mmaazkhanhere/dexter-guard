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


@pytest.mark.parametrize(
    ("transcript", "claim", "expected_status"),
    [
        ("Die Temperatur betrug 37,4 Grad Celsius.", "Die Temperatur betrug 38,4 Grad Celsius.", "CONTRADICTED"),
        ("Die Bewohnerin trank eine Tasse Tee und aß die Hälfte des Brotes.", "Die Bewohnerin nahm eine Tasse Tee und die Hälfte der Mahlzeit zu sich.", "SUPPORTED"),
    ],
)
def test_offline_fallback_handles_numeric_changes_and_supported_paraphrases(
    transcript: str, claim: str, expected_status: str,
) -> None:
    finding = OfflineSemanticEvidenceProvider().verify(
        claims=(_claim("claim-regression", claim),), source_text=transcript, run_id="run-regression",
        source_id="source-1", source_version=1,
    )["findings"][0]

    assert finding["status"] == expected_status


def test_offline_fallback_does_not_support_a_compound_claim_from_partial_overlap() -> None:
    result = OfflineSemanticEvidenceProvider().verify(
        claims=(_claim("claim-compound", "Die Bewohnerin berichtet über Schwindel und starke Brustschmerzen."),),
        source_text="Die Bewohnerin berichtet über Schwindel.",
        run_id="run-compound",
        source_id="source-1",
        source_version=1,
    )

    finding = result["findings"][0]
    assert finding["status"] == "UNCERTAIN"
    assert "OTHER" in finding["discrepancies"]


@pytest.mark.parametrize(
    ("transcript", "claim", "expected_status"),
    [
        (
            "Bis 10:00 Uhr trinkt die Bewohnerin insgesamt 500 ml Wasser und Tee.",
            "Bis 10:00 Uhr trank die Bewohnerin insgesamt 500ml Wasser und Tee.",
            "SUPPORTED",
        ),
        (
            "Bis 10:00 Uhr trinkt die Bewohnerin insgesamt 500 ml Wasser und Tee.",
            "Bis 10:00 Uhr trank die Bewohnerin insgesamt 700 ml Wasser und Tee.",
            "CONTRADICTED",
        ),
        (
            "Bis 10:00 Uhr trinkt die Bewohnerin insgesamt 500 ml Wasser.",
            "Um 10:00 Uhr trank die Bewohnerin insgesamt 500 ml Wasser.",
            "CONTRADICTED",
        ),
        (
            "Sie nimmt die Getränke selbstständig zu sich und bittet einmal um Unterstützung beim Öffnen des Bechers.",
            "Sie benötigte vollständige Unterstützung beim Trinken.",
            "CONTRADICTED",
        ),
        (
            "Übelkeit oder Erbrechen werden nicht beobachtet.",
            "Übelkeit wurde beobachtet.",
            "CONTRADICTED",
        ),
    ],
)
def test_offline_fallback_keeps_strict_numeric_temporal_negation_and_assistance_differences(
    transcript: str, claim: str, expected_status: str,
) -> None:
    finding = OfflineSemanticEvidenceProvider().verify(
        claims=(_claim("claim-strict", claim),),
        source_text=transcript,
        run_id="run-strict",
        source_id="source-1",
        source_version=1,
    )["findings"][0]

    assert finding["status"] == expected_status
    assert finding["sourceSpans"]


def test_oder_and_bzw_are_supported_as_alternative_drink_wording() -> None:
    source = "Bis 10:00 Uhr trank die Bewohnerin insgesamt 500ml Wasser oder Tee."
    claim = "Bis 10:00 Uhr wurde von der Bewohnerin insgesamt 500 ml Wasser bzw. Tee oral eingenommen."

    finding = OfflineSemanticEvidenceProvider().verify(
        claims=(_claim("claim-alternative-drinks", claim),),
        source_text=source,
        run_id="run-alternative-drinks",
        source_id="source-1",
        source_version=1,
    )["findings"][0]

    assert finding["status"] == "SUPPORTED"
    assert finding["sourceSpans"]


def test_und_and_oder_remain_a_meaningful_difference() -> None:
    source = "Bis 10:00 Uhr trank die Bewohnerin insgesamt 500ml Wasser und Tee."
    claim = "Bis 10:00 Uhr trank die Bewohnerin insgesamt 500 ml Wasser oder Tee."

    finding = OfflineSemanticEvidenceProvider().verify(
        claims=(_claim("claim-conjunction-change", claim),),
        source_text=source,
        run_id="run-conjunction-change",
        source_id="source-1",
        source_version=1,
    )["findings"][0]

    assert finding["status"] in {"CONTRADICTED", "UNCERTAIN"}
