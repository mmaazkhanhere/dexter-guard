import pytest

from human_review.policy import severity_for


@pytest.mark.parametrize(
    ("kwargs", "severity"),
    [
        ({"origin": "REVIEW_OPERATIONAL"}, "CRITICAL"),
        ({"origin": "SPEC_006", "policy_key": "MEASUREMENT_OMISSION"}, "CRITICAL"),
        ({"origin": "SPEC_006", "policy_key": "SYMPTOM_OMISSION"}, "MAJOR"),
        ({"origin": "SPEC_006", "status": "UNCERTAIN"}, "MAJOR"),
        ({"origin": "SPEC_005", "rule_code": "NUM-001"}, "MAJOR"),
        ({"origin": "SPEC_004", "status": "CONTRADICTED"}, "CRITICAL"),
        ({"origin": "SPEC_004", "status": "UNSUPPORTED"}, "MINOR"),
    ],
)
def test_severity_policy_maps_integrity_and_upstream_outcomes_deterministically(kwargs, severity):
    result, rationale = severity_for(**kwargs)
    assert result == severity
    assert rationale.startswith("REVIEW_SEVERITY-v1:")


def test_unknown_policy_inputs_are_safe_informational_findings():
    severity, rationale = severity_for(origin="UNKNOWN", status="UNKNOWN", rule_code="UNKNOWN")
    assert severity == "MINOR"
    assert "informational" in rationale
