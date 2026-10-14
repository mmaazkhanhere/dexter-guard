"""Deterministic, consequence-aware prioritization for review findings.

Severity is a review-priority label, not a clinical judgement or a measure of
verification confidence. Upstream evidence status remains unchanged.
"""

from collections.abc import Iterable

from .contracts import SEVERITY_POLICY_VERSION

_COVERAGE_CRITICAL = {"MEASUREMENT_OMISSION"}
_COVERAGE_MAJOR = {"SYMPTOM_OMISSION", "MOBILITY_ASSISTANCE_OMISSION", "CARE_ACTION_OMISSION", "UNCERTAINTY_OMISSION"}
_CRITICAL_NUMERIC_RULES = {"NUM-001", "NUM-003", "NUM-005"}
_MEDICATION_TERMS = frozenset({
    "insulin", "heparin", "metoprolol", "paracetamol", "medikament",
    "medikation", "injektion", "antikoagul",
})


def _high_consequence_reason(
    *, claim_text: str | None, discrepancy_codes: Iterable[str], rule_code: str | None,
    resident_misassignment: bool,
) -> str | None:
    codes = {code.upper() for code in discrepancy_codes}
    normalized_rule = (rule_code or "").upper()
    text = (claim_text or "").casefold()
    if resident_misassignment or normalized_rule.startswith(("RESIDENT-", "IDENTITY-")):
        return "resident identity mismatch"
    if "NEGATION" in codes:
        return "negation reversal"
    if normalized_rule in _CRITICAL_NUMERIC_RULES:
        return "incorrect measurement"
    if any(term in text for term in _MEDICATION_TERMS):
        return "medication documentation error"
    return None


def severity_for(
    *, origin: str, status: str | None = None, rule_code: str | None = None,
    policy_key: str | None = None, claim_text: str | None = None,
    discrepancy_codes: Iterable[str] = (), resident_misassignment: bool = False,
) -> tuple[str, str]:
    """Assign one deterministic severity without consulting detection confidence."""
    if origin == "REVIEW_OPERATIONAL" or (rule_code and (rule_code.startswith("EVD-") or rule_code.startswith("ALIGN-"))):
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: evidence or operational integrity failure"

    high_consequence = _high_consequence_reason(
        claim_text=claim_text,
        discrepancy_codes=discrepancy_codes,
        rule_code=rule_code,
        resident_misassignment=resident_misassignment,
    )
    if high_consequence:
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: high-consequence {high_consequence}"

    if origin == "SPEC_006":
        if policy_key in _COVERAGE_CRITICAL:
            return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: measurement omission"
        if policy_key in _COVERAGE_MAJOR or status in {"MISSING", "DISTORTED", "UNCERTAIN"}:
            return "MAJOR", f"{SEVERITY_POLICY_VERSION}: coverage requires review"
        if status == "INFORMATIONAL":
            return "MINOR", f"{SEVERITY_POLICY_VERSION}: informational coverage finding"
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: unknown upstream coverage finding"

    if origin == "SPEC_005":
        if rule_code and (rule_code.startswith("NUM-") or rule_code.startswith("STR-")):
            return "MAJOR", f"{SEVERITY_POLICY_VERSION}: deterministic validation failure"
        if rule_code and rule_code.startswith("INFO-"):
            return "MINOR", f"{SEVERITY_POLICY_VERSION}: informational deterministic finding"
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: unknown upstream deterministic finding"

    if origin == "SPEC_004":
        if status in {"CONTRADICTED", "UNSUPPORTED", "UNCERTAIN"}:
            return "MAJOR", f"{SEVERITY_POLICY_VERSION}: evidence finding requires review"
        if status == "INFORMATIONAL":
            return "MINOR", f"{SEVERITY_POLICY_VERSION}: informational evidence finding"
        return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: unknown upstream evidence finding"

    return "CRITICAL", f"{SEVERITY_POLICY_VERSION}: unknown upstream finding"
