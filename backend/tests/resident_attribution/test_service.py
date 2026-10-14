from types import SimpleNamespace

from resident_attribution import ResidentAttributionChecker


def _source(text: str):
    return SimpleNamespace(
        resident_test_id="synthetic-anna",
        resident_aliases={"synthetic-anna": ("Frau Anna Müller",), "synthetic-bruno": ("Herr Bruno Becker",)},
        transcript_text=text,
    )


def test_flags_claim_explicitly_assigned_to_another_synthetic_resident() -> None:
    findings = ResidentAttributionChecker().check(
        source=_source("Frau Anna Müller ist ruhig. Herr Bruno Becker klagt über Schmerzen."),
        claims=(SimpleNamespace(id="c1", claim_text="Herr Bruno Becker klagt über Schmerzen."),),
    )
    assert findings[0].outcome == "MISMATCH"
    assert findings[0].rule_code == "RESIDENT-001"
    assert findings[0].evidence


def test_requires_human_clarification_for_pronoun_with_multiple_residents() -> None:
    findings = ResidentAttributionChecker().check(
        source=_source("Frau Anna Müller ist ruhig. Herr Bruno Becker ist müde."),
        claims=(SimpleNamespace(id="c1", claim_text="Sie erhielt Unterstützung beim Trinken."),),
    )
    assert findings[0].outcome == "UNCERTAIN"
    assert findings[0].rule_code == "RESIDENT-002"


def test_does_not_guess_without_explicit_alias_mapping() -> None:
    source = SimpleNamespace(resident_test_id="synthetic-anna", resident_aliases={}, transcript_text="Frau Anna Müller ist ruhig. Herr Bruno Becker ist müde.")
    findings = ResidentAttributionChecker().check(source=source, claims=(SimpleNamespace(id="c1", claim_text="Sie ist müde."),))
    assert findings == ()
