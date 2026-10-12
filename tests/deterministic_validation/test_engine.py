from __future__ import annotations

from deterministic_validation.contracts import (
    Alignment,
    Approximation,
    Claim,
    EvidenceReference,
    SourceFact,
    TranscriptSnapshot,
)
from deterministic_validation.engine import DeterministicRuleEngine, normalize_measurement, parse_decimal, serialize_decimal, validate_evidence


SNAPSHOT = TranscriptSnapshot(sourceId="source-1", sourceVersion=1, transcriptText="Temperatur 37,2 °C. 😊")


def ref(ref_id: str = "evidence-1", *, start: int = 11, end: int = 15, **overrides: object) -> EvidenceReference:
    payload: dict[str, object] = {
        "evidenceReferenceId": ref_id,
        "sourceId": "source-1",
        "sourceVersion": 1,
        "start": start,
        "end": end,
        "quotedText": SNAPSHOT.transcript_text[start:end],
    }
    payload.update(overrides)
    return EvidenceReference.model_validate(payload)


def fact(value: str = "37,2", *, category: str = "TEMPERATURE", unit: str = "CELSIUS", approximation: str = "EXACT", evidence: tuple[EvidenceReference, ...] | None = None) -> SourceFact:
    return SourceFact(
        sourceId="source-1", sourceVersion=1, sourceFactId="fact-1",
        measurement={"category": category, "value": value, "unit": unit, "approximation": approximation},
        evidence=evidence or (ref(),),
    )


def claim(value: str = "37.2", *, category: str = "TEMPERATURE", unit: str = "CELSIUS", approximation: str = "EXACT", note_revision: int | None = 1, evidence: tuple[EvidenceReference, ...] = ()) -> Claim:
    return Claim(
        claimId="claim-1", noteId="note-1", noteRevision=note_revision,
        measurement={"category": category, "value": value, "unit": unit, "approximation": approximation},
        evidence=evidence,
    )


def alignment(status: str = "ALIGNED") -> Alignment:
    return Alignment(alignmentId="alignment-1", sourceFactId="fact-1", claimId="claim-1", status=status)


def findings(source: SourceFact, observed: Claim, pair: Alignment | None = None):
    return DeterministicRuleEngine().evaluate(SNAPSHOT, [source], [observed], [pair or alignment()])


def test_decimal_parsing_is_exact_and_accepts_comma_or_dot_without_locale_guessing() -> None:
    assert parse_decimal("0,5") == parse_decimal("0.5")
    assert serialize_decimal(parse_decimal("0001.5000")) == "1.5"
    assert parse_decimal("1.000,5") is None
    assert parse_decimal("ca. 1") is None


def test_equal_canonical_temperature_has_no_finding() -> None:
    assert findings(fact(), claim()) == ()


def test_numeric_mismatch_is_one_traceable_num001() -> None:
    result = findings(fact(), claim("38.2"))
    assert [(item.rule_id, item.outcome.value) for item in result] == [("NUM-001", "FAIL")]
    assert result[0].expected_value == "37.2"
    assert result[0].observed_value == "38.2"
    assert result[0].evidence_reference_ids == ("evidence-1",)


def test_fluid_litre_and_millilitre_are_equal_after_decimal_conversion() -> None:
    result = findings(fact("0,5", category="FLUID_INTAKE", unit="LITRE"), claim("500", category="FLUID_INTAKE", unit="MILLILITRE"))
    assert result == ()
    assert normalize_measurement(fact("0,5", category="FLUID_INTAKE", unit="LITRE").measurement).value == 500


def test_incompatible_category_dimensions_are_num003_and_invalid_pairing_is_str003() -> None:
    incompatible = findings(fact("500", category="FLUID_INTAKE", unit="MILLILITRE"), claim("500", category="MEDICATION_QUANTITY", unit="MILLIGRAM"))
    assert incompatible[0].rule_id == "NUM-003"
    invalid_pair = findings(fact("500", category="FLUID_INTAKE", unit="MILLILITRE"), claim("500", category="FLUID_INTAKE", unit="MILLIGRAM"))
    assert invalid_pair[0].rule_id == "STR-003"


def test_approximate_to_exact_is_num004_and_unspecified_is_not_evaluable() -> None:
    mismatch = findings(fact("200", category="FLUID_INTAKE", unit="MILLILITRE", approximation="APPROXIMATE"), claim("200", category="FLUID_INTAKE", unit="MILLILITRE", approximation="EXACT"))
    assert mismatch[0].rule_id == "NUM-004"
    assert mismatch[0].outcome.value == "FAIL"
    unavailable = findings(fact("200", category="FLUID_INTAKE", unit="MILLILITRE", approximation="UNSPECIFIED"), claim("200", category="FLUID_INTAKE", unit="MILLILITRE", approximation="EXACT"))
    assert unavailable[0].outcome.value == "NOT_EVALUABLE"


def test_blood_pressure_compares_components_without_clinical_range_logic() -> None:
    source = SourceFact(sourceId="source-1", sourceVersion=1, sourceFactId="fact-1", measurement={"category": "BLOOD_PRESSURE", "value": {"systolic": "120", "diastolic": 80}, "unit": "MMHG", "approximation": "EXACT"}, evidence=(ref(),))
    observed = Claim(claimId="claim-1", noteId="note-1", noteRevision=1, measurement={"category": "BLOOD_PRESSURE", "value": {"systolic": "140", "diastolic": 80}, "unit": "MMHG", "approximation": "EXACT"})
    result = findings(source, observed)
    assert result[0].rule_id == "NUM-005"
    assert "systolic" in result[0].message


def test_blood_pressure_components_must_be_positive_integers() -> None:
    source = SourceFact(sourceId="source-1", sourceVersion=1, sourceFactId="fact-1", measurement={"category": "BLOOD_PRESSURE", "value": {"systolic": "0", "diastolic": 80}, "unit": "MMHG", "approximation": "EXACT"}, evidence=(ref(),))
    observed = Claim(claimId="claim-1", noteId="note-1", noteRevision=1, measurement={"category": "BLOOD_PRESSURE", "value": {"systolic": "120", "diastolic": 80}, "unit": "MMHG", "approximation": "EXACT"})
    assert findings(source, observed)[0].rule_id == "STR-001"


def test_invalid_structured_value_skips_numeric_comparison() -> None:
    result = findings(fact("not-a-number"), claim("38.2"))
    assert result[0].rule_id == "STR-001"
    assert all(item.rule_id not in {"NUM-001", "NUM-002"} for item in result)


def test_alignment_gate_never_invents_numeric_contradiction() -> None:
    result = findings(fact(), claim("999"), alignment("AMBIGUOUS"))
    assert [item.rule_id for item in result] == ["ALIGN-001"]
    assert result[0].outcome.value == "NOT_EVALUABLE"


def test_evidence_uses_code_point_offsets_and_exact_quote() -> None:
    emoji_start = SNAPSHOT.transcript_text.index("😊")
    valid = ref("emoji", start=emoji_start, end=emoji_start + 1)
    assert findings(fact(evidence=(valid,)), claim()) == ()
    invalid_quote = ref("bad", quotedText="erfunden")
    result = findings(fact(evidence=(invalid_quote,)), claim())
    assert result[0].rule_id == "EVD-003"


def test_evidence_invalid_span_and_source_version_are_failures() -> None:
    empty = ref("empty", start=2, end=2, quotedText="")
    assert findings(fact(evidence=(empty,)), claim())[0].rule_id == "EVD-001"
    old = ref("old", sourceVersion=2)
    assert findings(fact(evidence=(old,)), claim())[0].rule_id == "EVD-002"
    out_of_range = ref("range", start=len(SNAPSHOT.transcript_text) - 1, end=len(SNAPSHOT.transcript_text) + 1, quotedText="x")
    assert validate_evidence(SNAPSHOT, out_of_range, source_fact_id="fact-1", claim_id=None).rule_id == "EVD-001"


def test_evidence_preserves_umlauts_combining_characters_and_non_bmp_code_points() -> None:
    snapshot = TranscriptSnapshot(sourceId="source-2", sourceVersion=1, transcriptText="Ärger e\u0301 😊")
    for ref_id, text in (("umlaut", "Ä"), ("combining", "e\u0301"), ("emoji", "😊")):
        start = snapshot.transcript_text.index(text)
        reference = EvidenceReference(
            evidenceReferenceId=ref_id, sourceId="source-2", sourceVersion=1,
            start=start, end=start + len(text), quotedText=text,
        )
        assert validate_evidence(snapshot, reference, source_fact_id="fact-2", claim_id=None) is None


def test_evidence_checks_are_after_comparison_findings_and_once_per_reference() -> None:
    shared = ref("shared")
    source = fact("38.2", evidence=(shared,))
    observed = claim("39.2", evidence=(shared,))
    result = findings(source, observed)
    assert [item.rule_id for item in result] == ["NUM-001"]


def test_rule_module_has_no_model_or_network_dependency() -> None:
    import deterministic_validation.engine as engine_module

    assert not {"openai", "httpx", "requests"}.intersection(engine_module.__dict__)

