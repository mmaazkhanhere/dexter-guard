from .contracts import SEVERITY_POLICY_VERSION

_COVERAGE_CRITICAL = {"MEASUREMENT_OMISSION"}
_COVERAGE_MAJOR = {"SYMPTOM_OMISSION", "MOBILITY_ASSISTANCE_OMISSION", "CARE_ACTION_OMISSION", "UNCERTAINTY_OMISSION"}


def severity_for(*, origin: str, status: str | None = None, rule_code: str | None = None, policy_key: str | None = None) -> tuple[str, str]:
    if origin == "REVIEW_OPERATIONAL" or (rule_code and (rule_code.startswith("EVD-") or rule_code.startswith("ALIGN-"))):
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: evidence or operational integrity failure"
    if origin == "SPEC_006":
        if policy_key in _COVERAGE_CRITICAL:
            return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: measurement omission"
        if policy_key in _COVERAGE_MAJOR or status in {"MISSING", "DISTORTED", "UNCERTAIN"}:
            return "MAJOR", f"{SEVERITY_POLICY_VERSION}: coverage requires review"
    if rule_code and (rule_code.startswith("NUM-") or rule_code.startswith("STR-")):
        return "MAJOR", f"{SEVERITY_POLICY_VERSION}: deterministic validation failure"
    if status in {"CONTRADICTED", "FAILED", "INVALID"}:
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: blocking verification outcome"
    return "MINOR", f"{SEVERITY_POLICY_VERSION}: informational finding"
