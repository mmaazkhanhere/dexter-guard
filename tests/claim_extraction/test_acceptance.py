"""Service-boundary acceptance coverage for CLM-001 through CLM-016."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

from claim_extraction.models import ExtractionStatus
from claim_extraction.service import ClaimExtractionService
from claim_extraction.spans import make_text_span
from tests.claim_extraction.test_service import Context, FakeReader


def _context(note: str, note_revision_id: str = "note-1:r1", resident: str = "resident-1") -> Context:
    return Context(
        note_revision_id=note_revision_id,
        note_body=note,
        note_body_hash=hashlib.sha256(note.encode("utf-8")).hexdigest(),
        resident_test_id=resident,
    )


def _claim(
    note: str,
    claim_id: str,
    category: str,
    start: int = 0,
    end: int | None = None,
    *,
    polarity: str = "AFFIRMED",
    negation: tuple[int, int] | None = None,
    certainty: str = "CERTAIN",
    certainty_cue: tuple[int, int] | None = None,
    attribution: str = "UNSPECIFIED",
    attribution_text: tuple[str, int, int] | None = None,
    numeric: dict[str, object] | None = None,
    medication: dict[str, str] | None = None,
) -> dict[str, object]:
    end = len(note) if end is None else end
    statement = make_text_span(note, start, end)
    payload: dict[str, object] = {
        "id": claim_id,
        "ordinal": 1,
        "category": category,
        "statementSpan": statement.model_dump(by_alias=True),
        "claimText": statement.text,
        "polarity": polarity,
        "certainty": certainty,
        "attribution": attribution,
        "numericValues": [],
        "extractionWarnings": [],
    }
    if negation is not None:
        payload["negationCue"] = make_text_span(note, *negation).model_dump(by_alias=True)
    if certainty_cue is not None:
        payload["certaintyCue"] = make_text_span(note, *certainty_cue).model_dump(by_alias=True)
    if attribution_text is not None:
        text, attr_start, attr_end = attribution_text
        payload["attributionText"] = text
        payload["attributionSpan"] = make_text_span(note, attr_start, attr_end).model_dump(by_alias=True)
    if numeric is not None:
        payload["numericValues"] = [numeric]
    if medication is not None:
        payload["medication"] = medication
    return payload


class ScenarioProvider:
    provider_version = "acceptance-provider-v1"
    model_version = "acceptance-model-v1"
    prompt_version = "claim-extraction-v1"

    def __init__(self, output: object):
        self.output = output
        self.calls = 0

    def extract(self, note_text: str, **_: object) -> object:
        self.calls += 1
        return self.output


def _service(note: str, output: object, *, resident: str = "resident-1", note_id: str = "note-1:r1"):
    context = _context(note, note_id, resident)
    provider = ScenarioProvider(output)
    extraction_service = ClaimExtractionService(FakeReader(context), provider, id_factory=lambda: "acceptance")
    return extraction_service.extract_claims(note_id), provider


def test_clm_001_one_atomic_affirmed_claim() -> None:
    note = "Bewohnerin ist wach."
    result, _ = _service(note, {"claims": [_claim(note, "c1", "OBSERVATION")]})
    assert result.status is ExtractionStatus.SUCCEEDED
    assert len(result.claims) == 1


def test_clm_002_and_clm_003_split_independent_assertions_and_allow_overlap() -> None:
    note = "Bewohnerin ist wach. Sie isst Frühstück."
    first_end = note.index(".") + 1
    second_start = first_end + 1
    first = _claim(note, "c1", "OBSERVATION", 0, first_end)
    second = _claim(note, "c2", "NUTRITION_HYDRATION", second_start)
    second["ordinal"] = 2
    result, _ = _service(note, {"claims": [first, second]})
    assert result.status is ExtractionStatus.SUCCEEDED
    assert [claim.ordinal for claim in result.claims] == [1, 2]

    note = "Bewohnerin ist wach und orientiert."
    claims = [_claim(note, "c1", "OBSERVATION", 0, note.index(" und")), _claim(note, "c2", "OBSERVATION", note.index("orientiert"), len(note))]
    claims[1]["ordinal"] = 2
    result, _ = _service(note, {"claims": claims})
    assert result.status is ExtractionStatus.SUCCEEDED
    assert len(result.claims) == 2


def test_clm_004_negation_is_not_affirmed_pain() -> None:
    note = "Kein Schmerz angegeben."
    result, _ = _service(note, {"claims": [_claim(note, "c1", "SYMPTOM", polarity="NEGATED", negation=(0, 4))]})
    assert result.claims[0].polarity.value == "NEGATED"
    assert result.claims[0].negation_cue.text == "Kein"


def test_clm_005_uncertainty_and_clm_006_resident_attribution_are_preserved() -> None:
    note = "Möglicherweise leichte Übelkeit."
    cue_end = len("Möglicherweise")
    result, _ = _service(note, {"claims": [_claim(note, "c1", "SYMPTOM", certainty="POSSIBLE", certainty_cue=(0, cue_end))]})
    assert result.claims[0].certainty.value == "POSSIBLE"
    assert result.claims[0].certainty_cue.text == "Möglicherweise"

    note = "Der Bewohner berichtet über Schwindel."
    attr_end = len("Der Bewohner berichtet")
    result, _ = _service(note, {"claims": [_claim(note, "c1", "SYMPTOM", attribution="CARE_RECIPIENT", attribution_text=("Der Bewohner berichtet", 0, attr_end))]})
    assert result.claims[0].attribution.value == "CARE_RECIPIENT"


def test_clm_007_and_008_preserve_decimal_comma_and_unit() -> None:
    note = "Temperatur 37,8 °C."
    value_start = note.index("37,8")
    unit_start = note.index("°C")
    numeric = {
        "raw": "37,8",
        "normalizedDecimal": "37.8",
        "unitRaw": "°C",
        "unitNormalized": "C",
        "approximation": False,
        "valueSpan": make_text_span(note, value_start, value_start + 4).model_dump(by_alias=True),
        "unitSpan": make_text_span(note, unit_start, unit_start + 2).model_dump(by_alias=True),
    }
    result, _ = _service(note, {"claims": [_claim(note, "c1", "VITAL_SIGN", numeric=numeric)]})
    value = result.claims[0].numeric_values[0]
    assert value.raw == "37,8"
    assert str(value.normalized_decimal) == "37.8"
    assert value.unit_raw == "°C"


def test_clm_009_extracts_conclusion_without_evidence_status() -> None:
    note = "Hinweis auf Harnwegsinfekt."
    result, _ = _service(note, {"claims": [_claim(note, "c1", "CLINICAL_CONCLUSION")]})
    assert result.claims[0].category.value == "CLINICAL_CONCLUSION"
    assert "supported" not in result.claims[0].model_fields_set


def test_clm_010_preserves_report_negation_without_splitting_away_context() -> None:
    note = "Bewohnerin berichtet keine Schmerzen beim Transfer."
    attr_text = "Bewohnerin berichtet"
    result, _ = _service(note, {"claims": [_claim(note, "c1", "SYMPTOM", polarity="NEGATED", negation=(22, 27), attribution="CARE_RECIPIENT", attribution_text=(attr_text, 0, len(attr_text)))]})
    assert result.claims[0].polarity.value == "NEGATED"
    assert result.claims[0].attribution.value == "CARE_RECIPIENT"


def test_clm_011_edited_revision_requires_a_new_result() -> None:
    note_one = "Bewohnerin ist wach."
    note_two = "Bewohnerin schläft."
    reader = FakeReader(_context(note_one, "note-1:r1"))
    provider = ScenarioProvider({"claims": [_claim(note_one, "c1", "OBSERVATION")]})
    run_ids = iter(("run-1", "run-2"))
    service = ClaimExtractionService(reader, provider, id_factory=lambda: next(run_ids))
    first = service.extract_claims("note-1:r1")
    reader.context = _context(note_two, "note-1:r2")
    provider.output = {"claims": [_claim(note_two, "c1", "SLEEP")]}
    second = service.extract_claims("note-1:r2")
    assert first.status is ExtractionStatus.SUCCEEDED
    assert second.status is ExtractionStatus.SUCCEEDED
    assert service.get_current_result("note-1:r1") is not None
    assert service.get_current_result("note-1:r2") is not None


def test_clm_012_invalid_json_is_failed_without_partial_claims() -> None:
    note = "Bewohnerin ist wach."
    result, _ = _service(note, "not-json")
    assert result.status is ExtractionStatus.FAILED
    assert result.error.code.value == "MALFORMED_PROVIDER_OUTPUT"
    assert result.claims == ()


def test_clm_013_and_013a_distinguish_empty_from_uncertain_empty() -> None:
    result, _ = _service("---", {"claims": []})
    assert result.status is ExtractionStatus.EMPTY

    result, _ = _service("Bewohnerin ist wach.", {"claims": []})
    assert result.status is ExtractionStatus.FAILED
    assert result.error.code.value == "INTERNAL_VALIDATION_ERROR"


def test_clm_014_preserves_medication_and_direct_administration_details() -> None:
    note = "Metoprolol 25 mg oral verabreicht."
    dose_start = note.index("25")
    numeric = {
        "raw": "25",
        "normalizedDecimal": "25",
        "unitRaw": "mg",
        "unitNormalized": "mg",
        "approximation": False,
        "valueSpan": make_text_span(note, dose_start, dose_start + 2).model_dump(by_alias=True),
        "unitSpan": make_text_span(note, dose_start + 3, dose_start + 5).model_dump(by_alias=True),
    }
    result, _ = _service(note, {"claims": [_claim(note, "c1", "MEDICATION", numeric=numeric, medication={"name": "Metoprolol", "doseRaw": "25 mg", "routeRaw": "oral", "administrationTemporalText": "verabreicht"})]})
    assert result.claims[0].medication.name == "Metoprolol"
    assert result.claims[0].medication.route_raw == "oral"


def test_clm_015_missing_resident_and_clm_016_timeout_are_typed_failures() -> None:
    note = "Bewohnerin ist wach."
    result, provider = _service(note, {"claims": []}, resident="")
    assert result.status is ExtractionStatus.FAILED
    assert result.error.code.value == "NON_SYNTHETIC_INPUT"
    assert provider.calls == 0

    class TimeoutProvider(ScenarioProvider):
        def extract(self, note_text: str, **kwargs: object) -> object:
            self.calls += 1
            raise TimeoutError()

    context = _context(note)
    provider = TimeoutProvider(None)
    result = ClaimExtractionService(FakeReader(context), provider, provider_timeout_seconds=0.1, max_provider_attempts=2).extract_claims("note-1:r1")
    assert result.status is ExtractionStatus.FAILED
    assert result.error.code.value == "PROVIDER_TIMEOUT"
    assert provider.calls == 2
