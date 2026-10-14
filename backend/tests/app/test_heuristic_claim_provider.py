from app.workflow import HeuristicClaimProvider


def test_compound_vital_signs_become_independent_numeric_claims() -> None:
    note = "Die Temperatur betr\u00e4gt 37,2 C und der Puls liegt bei 83 Schl\u00e4gen pro Minute."

    claims = HeuristicClaimProvider().extract(
        note,
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert [claim["claimText"] for claim in claims] == [
        "Die Temperatur betr\u00e4gt 37,2 C",
        "der Puls liegt bei 83 Schl\u00e4gen pro Minute.",
    ]
    assert [claim["numericValues"][0]["unitNormalized"] for claim in claims] == [
        "CELSIUS",
        "BEATS_PER_MINUTE",
    ]
    assert [claim["numericValues"][0]["normalizedDecimal"] for claim in claims] == ["37.2", "83"]
    assert all(len(claim["numericValues"]) == 1 for claim in claims)
    assert all(note[claim["statementSpan"]["startCodePoint"]:claim["statementSpan"]["endCodePointExclusive"]] == claim["claimText"] for claim in claims)


def test_coordinated_observations_become_independent_claims() -> None:
    claims = HeuristicClaimProvider().extract(
        "Die Bewohnerin ist wach und orientiert.",
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert [claim["claimText"] for claim in claims] == ["Die Bewohnerin ist wach", "orientiert."]


def test_multiple_medication_quantities_are_extracted_independently() -> None:
    claims = HeuristicClaimProvider().extract(
        "Metoprolol 25 mg oral verabreicht und Paracetamol 500 mg oral verabreicht.",
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert len(claims) == 2
    assert [claim["numericValues"][0]["normalizedDecimal"] for claim in claims] == ["25", "500"]
    assert all(claim["category"] == "MEASUREMENT" for claim in claims)


def test_multiple_reported_symptoms_are_extracted_independently() -> None:
    claims = HeuristicClaimProvider().extract(
        "Die Bewohnerin berichtet Schwindel und Übelkeit.",
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert [claim["claimText"] for claim in claims] == [
        "Die Bewohnerin berichtet Schwindel",
        "Übelkeit.",
    ]
    assert all(claim["category"] == "SYMPTOM" for claim in claims)


def test_three_measurements_in_one_sentence_keep_three_values() -> None:
    claims = HeuristicClaimProvider().extract(
        "Temperatur 37,2 C und Puls 83 bpm und Trinkmenge 250 ml.",
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert len(claims) == 3
    assert [claim["numericValues"][0]["normalizedDecimal"] for claim in claims] == ["37.2", "83", "250"]
    assert [claim["numericValues"][0]["unitNormalized"] for claim in claims] == [
        "CELSIUS",
        "BEATS_PER_MINUTE",
        "MILLILITRE",
    ]
