from claim_extraction.models import Claim
from claim_extraction.spans import make_text_span
from claim_extraction.validator import validate_claims


def test_uncertainty_attribution_temporal_measurement_and_medication_are_preserved() -> None:
    note = "Vermutlich etwa 1,5 l getrunken; Pflegekraft beobachtet Husten."
    statement = make_text_span(note, 0, len(note))
    certainty = make_text_span(note, 0, len("Vermutlich"))
    value_start = note.index("etwa")
    value = make_text_span(note, value_start, value_start + len("etwa 1,5"))
    unit = make_text_span(note, value_start + len("etwa 1,5 "), value_start + len("etwa 1,5 l"))
    attribution_text = "Pflegekraft beobachtet"
    attribution_start = note.index(attribution_text)
    attribution = make_text_span(note, attribution_start, attribution_start + len(attribution_text))
    raw_claim = {
        "id": "note-1:r1:c1",
        "noteRevisionId": "note-1:r1",
        "residentTestId": "resident-1",
        "ordinal": 1,
        "category": "NUTRITION_HYDRATION",
        "statementSpan": statement.model_dump(by_alias=True),
        "claimText": statement.text,
        "polarity": "AFFIRMED",
        "certainty": "POSSIBLE",
        "certaintyCue": certainty.model_dump(by_alias=True),
        "attribution": "CAREGIVER",
        "attributionText": attribution_text,
        "attributionSpan": attribution.model_dump(by_alias=True),
        "temporalText": "Vermutlich",
        "temporalSpan": certainty.model_dump(by_alias=True),
        "numericValues": [{
            "raw": value.text,
            "normalizedDecimal": "1.5",
            "unitRaw": "l",
            "unitNormalized": "L",
            "approximation": True,
            "valueSpan": value.model_dump(by_alias=True),
            "unitSpan": unit.model_dump(by_alias=True),
        }],
        "medication": None,
        "extractionWarnings": [],
    }
    claims = validate_claims([raw_claim], type("Context", (), {
        "note_revision_id": "note-1:r1",
        "note_body": note,
        "resident_test_id": "resident-1",
    })())
    assert claims[0].certainty.value == "POSSIBLE"
    assert claims[0].attribution.value == "CAREGIVER"
    assert claims[0].numeric_values[0].raw == "etwa 1,5"
    assert claims[0].numeric_values[0].normalized_decimal == 1.5


def test_claim_contract_has_no_evidence_verdict_or_diagnosis_fields() -> None:
    forbidden = {"supported", "contradicted", "evidenceStatus", "diagnosis", "approvalState"}
    assert forbidden.isdisjoint(Claim.model_fields)
