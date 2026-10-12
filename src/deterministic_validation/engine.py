"""Pure, deterministic rules for aligned structured measurements and evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .contracts import (
    Alignment, AlignmentStatus, Approximation, Claim, EvidenceReference, Measurement,
    MeasurementCategory, Outcome, ReasonCode, ScalarMeasurement, SourceFact,
    TranscriptSnapshot, Unit, ValidationFinding,
)

_DECIMAL_PATTERN = re.compile(r"^[+-]?(?:0|[0-9]+)(?:[.,][0-9]+)?$")
_INTEGER_PATTERN = re.compile(r"^[+-]?[0-9]+$")
_CATEGORY_UNITS: dict[MeasurementCategory, frozenset[Unit]] = {
    MeasurementCategory.TEMPERATURE: frozenset({Unit.CELSIUS}),
    MeasurementCategory.FLUID_INTAKE: frozenset({Unit.MILLILITRE, Unit.LITRE}),
    MeasurementCategory.MEDICATION_QUANTITY: frozenset({Unit.MILLIGRAM, Unit.GRAM}),
    MeasurementCategory.BLOOD_PRESSURE: frozenset({Unit.MMHG}),
}
_CANONICAL_UNITS = {
    MeasurementCategory.TEMPERATURE: Unit.CELSIUS,
    MeasurementCategory.FLUID_INTAKE: Unit.MILLILITRE,
    MeasurementCategory.MEDICATION_QUANTITY: Unit.MILLIGRAM,
    MeasurementCategory.BLOOD_PRESSURE: Unit.MMHG,
}
_CONVERSION_FACTORS = {
    (Unit.MILLILITRE, Unit.MILLILITRE): Decimal("1"),
    (Unit.LITRE, Unit.MILLILITRE): Decimal("1000"),
    (Unit.MILLIGRAM, Unit.MILLIGRAM): Decimal("1"),
    (Unit.GRAM, Unit.MILLIGRAM): Decimal("1000"),
    (Unit.CELSIUS, Unit.CELSIUS): Decimal("1"),
    (Unit.MMHG, Unit.MMHG): Decimal("1"),
}


@dataclass(frozen=True)
class CanonicalScalar:
    value: Decimal
    unit: Unit
    converted: bool


@dataclass(frozen=True)
class CanonicalBloodPressure:
    systolic: int
    diastolic: int
    unit: Unit
    converted: bool = False


@dataclass(frozen=True)
class RuleTrace:
    rule_id: str
    outcome: Outcome
    message: str


def parse_decimal(value: str) -> Decimal | None:
    if not _DECIMAL_PATTERN.fullmatch(value):
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def serialize_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def parse_blood_pressure_component(value: int | str) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value > 0 else None
    if not isinstance(value, str) or not _INTEGER_PATTERN.fullmatch(value):
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def category_unit_is_valid(measurement: Measurement) -> bool:
    return measurement.unit in _CATEGORY_UNITS[measurement.category]


def normalize_measurement(measurement: Measurement) -> CanonicalScalar | CanonicalBloodPressure | None:
    if not category_unit_is_valid(measurement):
        return None
    canonical_unit = _CANONICAL_UNITS[measurement.category]
    factor = _CONVERSION_FACTORS.get((measurement.unit, canonical_unit))
    if factor is None:
        return None
    if isinstance(measurement, ScalarMeasurement):
        parsed = parse_decimal(measurement.value)
        return None if parsed is None else CanonicalScalar(parsed * factor, canonical_unit, measurement.unit != canonical_unit)
    systolic = parse_blood_pressure_component(measurement.value.systolic)
    diastolic = parse_blood_pressure_component(measurement.value.diastolic)
    if systolic is None or diastolic is None:
        return None
    return CanonicalBloodPressure(systolic, diastolic, canonical_unit)


def conversion_trace(source: Measurement, observed: Measurement) -> RuleTrace | None:
    """Return the optional NUM-002 PASS trace; public findings omit PASS records."""

    source_canonical = normalize_measurement(source)
    observed_canonical = normalize_measurement(observed)
    if source_canonical is None or observed_canonical is None:
        return None
    source_converted = getattr(source_canonical, "converted", False)
    observed_converted = getattr(observed_canonical, "converted", False)
    if not source_converted and not observed_converted:
        return None
    return RuleTrace("NUM-002", Outcome.PASS, "A permitted exact unit conversion was applied before comparison.")


def _raw_value(measurement: Measurement) -> str | dict[str, int | str]:
    if isinstance(measurement, ScalarMeasurement):
        return measurement.value
    return {"systolic": measurement.value.systolic, "diastolic": measurement.value.diastolic}


def _evidence_ids(source_fact: SourceFact, claim: Claim) -> tuple[str, ...]:
    return tuple(dict.fromkeys(ref.evidence_reference_id for ref in (*source_fact.evidence, *claim.evidence)))


def _finding(*, rule_id: str, outcome: Outcome, source_fact_id: str | None, claim_id: str | None,
             alignment_id: str | None, evidence_reference_ids: tuple[str, ...], expected_value: object | None,
             observed_value: object | None, unit: str | None, reason_code: ReasonCode, message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id, rule_version="1", ruleset_version="DVE-RULESET-v1", outcome=outcome,
        source_fact_id=source_fact_id, claim_id=claim_id, alignment_id=alignment_id,
        evidence_reference_ids=evidence_reference_ids, expected_value=expected_value,
        observed_value=observed_value, unit=unit, requires_review=True,
        reason_code=reason_code, message=message,
    )


def _alignment_finding(alignment: Alignment, source_fact: SourceFact | None, claim: Claim | None) -> ValidationFinding:
    reason = {
        AlignmentStatus.UNAVAILABLE: ReasonCode.ALIGNMENT_UNAVAILABLE,
        AlignmentStatus.AMBIGUOUS: ReasonCode.ALIGNMENT_AMBIGUOUS,
        AlignmentStatus.REJECTED: ReasonCode.ALIGNMENT_REJECTED,
    }[alignment.status]
    evidence_ids = _evidence_ids(source_fact, claim) if source_fact is not None and claim is not None else ()
    return _finding(rule_id="ALIGN-001", outcome=Outcome.NOT_EVALUABLE,
                    source_fact_id=alignment.source_fact_id, claim_id=alignment.claim_id,
                    alignment_id=alignment.alignment_id, evidence_reference_ids=evidence_ids,
                    expected_value=None, observed_value=None, unit=None, reason_code=reason,
                    message=f"Alignment status {alignment.status.value} does not permit deterministic comparison.")


def _structural_findings(alignment: Alignment, source_fact: SourceFact, claim: Claim) -> tuple[ValidationFinding, ...]:
    evidence_ids = _evidence_ids(source_fact, claim)
    findings: list[ValidationFinding] = []
    if claim.note_revision is None:
        findings.append(_finding(rule_id="STR-002", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                                 claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                 evidence_reference_ids=evidence_ids, expected_value="positive note revision",
                                 observed_value=None, unit=None, reason_code=ReasonCode.MISSING_REQUIRED_REFERENCE,
                                 message="The resolved claim has no note revision reference."))
    if not category_unit_is_valid(source_fact.measurement) or not category_unit_is_valid(claim.measurement):
        findings.append(_finding(rule_id="STR-003", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                                 claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                 evidence_reference_ids=evidence_ids, expected_value=_raw_value(source_fact.measurement),
                                 observed_value=_raw_value(claim.measurement),
                                 unit=f"{source_fact.measurement.unit.value}/{claim.measurement.unit.value}",
                                 reason_code=ReasonCode.INVALID_UNIT_CATEGORY_PAIRING,
                                 message="A measurement uses a unit that is not permitted for its category."))
    if normalize_measurement(source_fact.measurement) is None or normalize_measurement(claim.measurement) is None:
        if not any(item.rule_id == "STR-003" for item in findings):
            findings.append(_finding(rule_id="STR-001", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                                     claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                     evidence_reference_ids=evidence_ids, expected_value=_raw_value(source_fact.measurement),
                                     observed_value=_raw_value(claim.measurement), unit=None,
                                     reason_code=ReasonCode.INVALID_STRUCTURED_FIELD_TYPE,
                                     message="A structured measurement value cannot be parsed deterministically."))
    return tuple(findings)


def _numeric_findings(alignment: Alignment, source_fact: SourceFact, claim: Claim) -> tuple[ValidationFinding, ...]:
    structural = _structural_findings(alignment, source_fact, claim)
    if structural:
        return structural
    evidence_ids = _evidence_ids(source_fact, claim)
    source_measurement, claim_measurement = source_fact.measurement, claim.measurement
    if source_measurement.category != claim_measurement.category:
        return (_finding(rule_id="NUM-003", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                          claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                          evidence_reference_ids=evidence_ids, expected_value=_raw_value(source_measurement),
                          observed_value=_raw_value(claim_measurement),
                          unit=f"{source_measurement.unit.value}/{claim_measurement.unit.value}",
                          reason_code=ReasonCode.INCOMPATIBLE_UNIT,
                          message="Aligned measurements have incompatible categories or unit dimensions."),)
    source, observed = normalize_measurement(source_measurement), normalize_measurement(claim_measurement)
    assert source is not None and observed is not None
    findings: list[ValidationFinding] = []
    if isinstance(source, CanonicalScalar) and isinstance(observed, CanonicalScalar) and source.value != observed.value:
        findings.append(_finding(rule_id="NUM-001", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                                 claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                 evidence_reference_ids=evidence_ids, expected_value=serialize_decimal(source.value),
                                 observed_value=serialize_decimal(observed.value), unit=source.unit.value,
                                 reason_code=ReasonCode.NUMERIC_MISMATCH,
                                 message="Canonical scalar measurement differs from the source fact."))
    elif isinstance(source, CanonicalBloodPressure) and isinstance(observed, CanonicalBloodPressure):
        changed = [name for name, left, right in (("systolic", source.systolic, observed.systolic),
                                                    ("diastolic", source.diastolic, observed.diastolic)) if left != right]
        if changed:
            findings.append(_finding(rule_id="NUM-005", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                                     claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                     evidence_reference_ids=evidence_ids,
                                     expected_value={"systolic": source.systolic, "diastolic": source.diastolic},
                                     observed_value={"systolic": observed.systolic, "diastolic": observed.diastolic},
                                     unit=source.unit.value, reason_code=ReasonCode.COMPOSITE_MEASUREMENT_MISMATCH,
                                     message=f"Blood-pressure component(s) differ: {', '.join(changed)}."))
    if source_measurement.approximation is Approximation.UNSPECIFIED or claim_measurement.approximation is Approximation.UNSPECIFIED:
        findings.append(_finding(rule_id="NUM-004", outcome=Outcome.NOT_EVALUABLE, source_fact_id=source_fact.source_fact_id,
                                 claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                 evidence_reference_ids=evidence_ids, expected_value=source_measurement.approximation.value,
                                 observed_value=claim_measurement.approximation.value, unit=source.unit.value,
                                 reason_code=ReasonCode.PRECISION_MISMATCH,
                                 message="Approximation comparison is not evaluable because a structured state is unspecified."))
    elif source_measurement.approximation is Approximation.APPROXIMATE and claim_measurement.approximation is Approximation.EXACT:
        findings.append(_finding(rule_id="NUM-004", outcome=Outcome.FAIL, source_fact_id=source_fact.source_fact_id,
                                 claim_id=claim.claim_id, alignment_id=alignment.alignment_id,
                                 evidence_reference_ids=evidence_ids, expected_value=source_measurement.approximation.value,
                                 observed_value=claim_measurement.approximation.value, unit=source.unit.value,
                                 reason_code=ReasonCode.PRECISION_MISMATCH,
                                 message="An approximate source measurement was represented as exact."))
    return tuple(findings)


def _evidence_finding(*, rule_id: str, source_fact_id: str | None, claim_id: str | None,
                      reference: EvidenceReference, reason_code: ReasonCode, message: str,
                      expected_value: object | None = None, observed_value: object | None = None) -> ValidationFinding:
    return _finding(rule_id=rule_id, outcome=Outcome.FAIL, source_fact_id=source_fact_id, claim_id=claim_id,
                    alignment_id=None, evidence_reference_ids=(reference.evidence_reference_id,),
                    expected_value=expected_value, observed_value=observed_value, unit=None,
                    reason_code=reason_code, message=message)


def validate_evidence(snapshot: TranscriptSnapshot, reference: EvidenceReference, *,
                      source_fact_id: str | None, claim_id: str | None) -> ValidationFinding | None:
    if reference.start < 0 or reference.end <= reference.start or reference.end > len(snapshot.transcript_text):
        return _evidence_finding(rule_id="EVD-001", source_fact_id=source_fact_id, claim_id=claim_id,
                                 reference=reference, reason_code=ReasonCode.INVALID_SOURCE_SPAN,
                                 message="Evidence span is empty, reversed, negative, or outside the immutable transcript.")
    if reference.source_id != snapshot.source_id or reference.source_version != snapshot.source_version:
        return _evidence_finding(rule_id="EVD-002", source_fact_id=source_fact_id, claim_id=claim_id,
                                 reference=reference, reason_code=ReasonCode.SOURCE_VERSION_MISMATCH,
                                 message="Evidence reference does not identify the immutable validation source version.")
    authoritative_text = snapshot.transcript_text[reference.start:reference.end]
    if reference.quoted_text != authoritative_text:
        return _evidence_finding(rule_id="EVD-003", source_fact_id=source_fact_id, claim_id=claim_id,
                                 reference=reference, reason_code=ReasonCode.EVIDENCE_TEXT_MISMATCH,
                                 message="Evidence quotation is not equal to the authoritative source substring.",
                                 expected_value=authoritative_text, observed_value=reference.quoted_text)
    return None


class DeterministicRuleEngine:
    """Evaluate only explicit pairs and immutable evidence references."""

    def evaluate(self, snapshot: TranscriptSnapshot, facts: Iterable[SourceFact], claims: Iterable[Claim],
                 alignments: Iterable[Alignment]) -> tuple[ValidationFinding, ...]:
        facts = tuple(facts)
        claims = tuple(claims)
        facts_by_id, claims_by_id = {item.source_fact_id: item for item in facts}, {item.claim_id: item for item in claims}
        comparison_findings: list[ValidationFinding] = []
        for alignment in alignments:
            source_fact, claim = facts_by_id.get(alignment.source_fact_id), claims_by_id.get(alignment.claim_id)
            if alignment.status is not AlignmentStatus.ALIGNED:
                comparison_findings.append(_alignment_finding(alignment, source_fact, claim))
            elif source_fact is not None and claim is not None:
                comparison_findings.extend(_numeric_findings(alignment, source_fact, claim))
        evidence_findings: list[ValidationFinding] = []
        seen: set[str] = set()
        owners = [(item, None) for item in facts] + [(None, item) for item in claims]
        for source_fact, claim in owners:
            references = source_fact.evidence if source_fact is not None else claim.evidence
            for reference in references:
                if reference.evidence_reference_id in seen:
                    continue
                seen.add(reference.evidence_reference_id)
                finding = validate_evidence(snapshot, reference,
                                            source_fact_id=source_fact.source_fact_id if source_fact else None,
                                            claim_id=claim.claim_id if claim else None)
                if finding is not None:
                    evidence_findings.append(finding)
        return tuple(comparison_findings + evidence_findings)


__all__ = ["CanonicalBloodPressure", "CanonicalScalar", "DeterministicRuleEngine", "RuleTrace",
           "category_unit_is_valid", "conversion_trace", "normalize_measurement",
           "parse_blood_pressure_component", "parse_decimal", "serialize_decimal", "validate_evidence"]

