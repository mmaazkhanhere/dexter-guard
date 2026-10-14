import pytest

from human_review.policy import severity_for


@pytest.mark.parametrize(
    ("kwargs", "severity"),
    [
        ({"origin": "REVIEW_OPERATIONAL"}, "CRITICAL"),
        ({"origin": "SPEC_006", "policy_key": "MEASUREMENT_OMISSION"}, "CRITICAL"),
        ({"origin": "SPEC_006", "policy_key": "SYMPTOM_OMISSION"}, "MAJOR"),
        ({"origin": "SPEC_006", "status": "UNCERTAIN"}, "MAJOR"),
        ({"origin": "SPEC_005", "rule_code": "NUM-001"}, "CRITICAL"),
        ({"origin": "SPEC_005", "rule_code": "NUM-004"}, "MAJOR"),
        ({"origin": "SPEC_004", "status": "CONTRADICTED"}, "MAJOR"),
        ({"origin": "SPEC_004", "status": "UNSUPPORTED"}, "MAJOR"),
    ],
)
def test_severity_policy_maps_integrity_and_upstream_outcomes_deterministically(kwargs, severity):
    result, rationale = severity_for(**kwargs)
    assert result == severity
    assert rationale.startswith("REVIEW_SEVERITY-v2:")


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "origin": "SPEC_004",
            "status": "CONTRADICTED",
            "claim_text": "Insulin wurde verabreicht.",
            "discrepancy_codes": ("NEGATION",),
        },
        {
            "origin": "SPEC_004",
            "status": "UNCERTAIN",
            "claim_text": "Insulin wurde verabreicht.",
        },
        {"origin": "SPEC_004", "status": "CONTRADICTED", "discrepancy_codes": ("NEGATION",)},
        {"origin": "SPEC_004", "status": "UNSUPPORTED", "rule_code": "RESIDENT-001"},
    ],
)
def test_high_consequence_errors_are_critical_independent_of_evidence_status(kwargs):
    severity, rationale = severity_for(**kwargs)
    assert severity == "CRITICAL"
    assert "high-consequence" in rationale


def test_unknown_policy_inputs_fail_closed():
    severity, rationale = severity_for(origin="UNKNOWN", status="UNKNOWN", rule_code="UNKNOWN")
    assert severity == "CRITICAL"
    assert "unknown upstream" in rationale
