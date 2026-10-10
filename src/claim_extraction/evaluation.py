"""Reproducible, feature-level extraction metrics for labeled synthetic cases."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .models import Claim, ExtractionResult
from .spans import validate_text_span


@dataclass(frozen=True)
class ExtractionEvaluationMetrics:
    claim_identification_precision: float
    claim_identification_recall: float
    claim_atomicity_correctness: float
    negation_accuracy: float
    certainty_preservation: float
    attribution_accuracy: float
    numerical_extraction_accuracy: float
    character_span_validity: float
    structured_output_success_rate: float
    structured_output_failure_rate: float
    case_count: int


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def evaluate_case(expected: Mapping[str, object], result: ExtractionResult, note_text: str) -> dict[str, float]:
    """Score one labeled case using exact contract-level properties.

    The function measures extraction structure and semantic preservation only. It
    does not assess clinical correctness or evidence support.
    """

    expected_count = int(expected.get("expected_claims", 1 if expected.get("id") else 0))
    actual_count = len(result.claims)
    claims: tuple[Claim, ...] = result.claims
    span_valid = sum(_valid_claim_spans(claim, note_text) for claim in claims)
    negation_expected = expected.get("expected_negation")
    negation_actual = any(claim.polarity.value == "NEGATED" for claim in claims)
    certainty_expected = expected.get("expected_uncertainty")
    certainty_actual = any(claim.certainty.value in {"UNCERTAIN", "POSSIBLE"} for claim in claims)
    attribution_expected = expected.get("expected_attribution")
    attribution_actual = any(claim.attribution.value == attribution_expected for claim in claims)
    numeric_expected = expected.get("expected_numeric")
    numeric_actual = any(value.raw == numeric_expected for claim in claims for value in claim.numeric_values)
    return {
        "claim_identification_precision": _ratio(min(actual_count, expected_count), actual_count),
        "claim_identification_recall": _ratio(min(actual_count, expected_count), expected_count),
        "claim_atomicity_correctness": float(actual_count == expected_count),
        "negation_accuracy": float(negation_actual == bool(negation_expected)),
        "certainty_preservation": float(certainty_actual == bool(certainty_expected)),
        "attribution_accuracy": float(attribution_actual == bool(attribution_expected)),
        "numerical_extraction_accuracy": float(numeric_actual == bool(numeric_expected)),
        "character_span_validity": _ratio(span_valid, actual_count),
        "structured_output_success_rate": float(result.status.value in {"SUCCEEDED", "EMPTY"}),
        "structured_output_failure_rate": float(result.status.value == "FAILED"),
    }


def aggregate_metrics(scores: Iterable[Mapping[str, float]]) -> ExtractionEvaluationMetrics:
    rows = list(scores)
    if not rows:
        return ExtractionEvaluationMetrics(*(0.0 for _ in range(10)), case_count=0)
    names = (
        "claim_identification_precision",
        "claim_identification_recall",
        "claim_atomicity_correctness",
        "negation_accuracy",
        "certainty_preservation",
        "attribution_accuracy",
        "numerical_extraction_accuracy",
        "character_span_validity",
        "structured_output_success_rate",
        "structured_output_failure_rate",
    )
    means = [sum(row[name] for row in rows) / len(rows) for name in names]
    return ExtractionEvaluationMetrics(*means, case_count=len(rows))


def _valid_claim_spans(claim: Claim, note_text: str) -> int:
    try:
        validate_text_span(claim.statement_span, note_text)
        for cue in (claim.negation_cue, claim.certainty_cue, claim.attribution_span, claim.temporal_span):
            if cue is not None:
                validate_text_span(cue, note_text)
        for numeric in claim.numeric_values:
            validate_text_span(numeric.value_span, note_text)
            if numeric.unit_span is not None:
                validate_text_span(numeric.unit_span, note_text)
    except Exception:
        return 0
    return 1
