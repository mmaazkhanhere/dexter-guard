from .fixtures.review_cases import SCENARIOS, SYNTHETIC_NOTE, SYNTHETIC_TRANSCRIPT


def test_hr_fixture_manifest_covers_every_spec_scenario_with_audit_expectation():
    assert [scenario.scenario_id for scenario in SCENARIOS] == [f"HR-{index:03}" for index in range(1, 19)]
    assert all(scenario.expected_outcome and scenario.expected_audit_event for scenario in SCENARIOS)
    assert all(scenario.source_id and scenario.note_id and scenario.run_ids for scenario in SCENARIOS)
    assert all(scenario.source_version == scenario.note_revision == 1 for scenario in SCENARIOS)


def test_hr_fixture_text_is_synthetic_and_uses_no_identifying_fields():
    combined = f"{SYNTHETIC_TRANSCRIPT} {SYNTHETIC_NOTE}".lower()
    assert "bewohnerin a" in combined
    assert all(token not in combined for token in ("@", "geburtsdatum", "adresse", "telefon"))
