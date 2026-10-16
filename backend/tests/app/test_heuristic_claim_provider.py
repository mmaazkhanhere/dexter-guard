from app.workflow import HeuristicClaimProvider


def test_german_abbreviations_do_not_break_claim_boundaries_or_offsets() -> None:
    note = (
        "Bis 10:00 Uhr wurde von der Bewohnerin insgesamt 500 ml Wasser bzw. Tee oral eingenommen. "
        "Die Bewohnerin erhielt z. B. Tee und u. a. Wasser. Danach blieb sie ruhig usw."
    )

    claims = HeuristicClaimProvider().extract(
        note, note_revision_id="note-1:r1", resident_test_id="resident-1",
    )["claims"]

    assert [claim["claimText"] for claim in claims] == [
        "Bis 10:00 Uhr wurde von der Bewohnerin insgesamt 500 ml Wasser bzw. Tee oral eingenommen.",
        "Die Bewohnerin erhielt z. B. Tee und u. a. Wasser.",
        "Danach blieb sie ruhig usw.",
    ]
    assert all(
        note[claim["statementSpan"]["startCodePoint"]:claim["statementSpan"]["endCodePointExclusive"]] == claim["claimText"]
        for claim in claims
    )


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


def test_contrastive_negated_symptoms_keep_independent_negation_scopes() -> None:
    note = "Keine Schmerzen, aber keine Übelkeit."

    claims = HeuristicClaimProvider().extract(
        note,
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert [claim["claimText"] for claim in claims] == ["Keine Schmerzen", "keine Übelkeit."]
    assert [claim["polarity"] for claim in claims] == ["NEGATED", "NEGATED"]
    assert [claim["negationCue"]["text"] for claim in claims] == ["Keine", "keine"]
    assert all(note[claim["statementSpan"]["startCodePoint"]:claim["statementSpan"]["endCodePointExclusive"]] == claim["claimText"] for claim in claims)


def test_fluid_intake_with_time_boundary_and_assistance_is_extracted_as_scoped_atomic_claims() -> None:
    note = (
        "Bis 10:00 Uhr trank die Bewohnerin insgesamt 500ml Wasser und Tee. "
        "Sie nahm die Getränke selbstständig zu sich und bat einmal um Unterstützung beim Öffnen des Bechers. "
        "Übelkeit oder Erbrechen wurden nicht beobachtet."
    )

    claims = HeuristicClaimProvider().extract(
        note,
        note_revision_id="note-1:r1",
        resident_test_id="resident-1",
    )["claims"]

    assert [claim["claimText"] for claim in claims] == [
        "Bis 10:00 Uhr",
        "Bis 10:00 Uhr trank die Bewohnerin insgesamt 500ml Wasser und Tee.",
        "Wasser und Tee",
        "Sie nahm die Getränke selbstständig zu sich",
        "bat einmal um Unterstützung beim Öffnen des Bechers.",
        "Übelkeit oder Erbrechen wurden nicht beobachtet.",
    ]
    assert claims[0]["temporalText"] == "Bis 10:00 Uhr"
    assert claims[1]["numericValues"][0]["normalizedDecimal"] == "500"
    assert all(note[claim["statementSpan"]["startCodePoint"]:claim["statementSpan"]["endCodePointExclusive"]] == claim["claimText"] for claim in claims)
