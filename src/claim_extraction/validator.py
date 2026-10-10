"""Deterministic validation of untrusted structured claim output."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from .models import Claim, NumericValue, TextSpan
from .revision_reader import NoteRevisionContext
from .spans import SpanValidationError, parse_text_span, validate_text_span


class ClaimValidationError(ValueError):
    """Raised when any claim makes the provider response unsafe to accept."""


class InvalidClaimSpanError(ClaimValidationError):
    """Raised when a structurally valid span does not match the immutable note."""


_NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
_APPROXIMATION_PATTERN = re.compile(r"(?:\bca\.?\b|\betwa\b|\bungef[aä]hr\b|\bcirca\b|~)", re.IGNORECASE)
_NEGATION_PATTERN = re.compile(
    r"\b(?:kein(?:e|en|em|er|es)?|nicht|ohne|verneint(?:e|et)?|nein)\b",
    re.IGNORECASE,
)
_HEDGING_PATTERN = re.compile(
    r"\b(?:vielleicht|möglicherweise|vermutlich|wahrscheinlich|eventuell|scheinbar|anscheinend)\b",
    re.IGNORECASE,
)
_APPROXIMATION_ONLY_PATTERN = re.compile(
    r"(?:\bca\.?\b|\betwa\b|\bungef[aä]hr\b|\bcirca\b|~)",
    re.IGNORECASE,
)
_CARE_RECIPIENT_PATTERN = re.compile(
    r"\b(?:bewohner(?:in|en)?|resident(?:in)?|patient(?:in)?|selbst)\b|\b(?:berichtet|gibt an|äußert)",
    re.IGNORECASE,
)
_CAREGIVER_PATTERN = re.compile(
    r"\b(?:pflegekraft|pflegepersonal|betreuung|mitarbeiter(?:in)?|schwester)\b|\b(?:beobachtet|versorgt|misst)",
    re.IGNORECASE,
)


def _context_value(context: NoteRevisionContext | Any, name: str) -> Any:
    return getattr(context, name)


def _within_statement(span: TextSpan, statement: TextSpan) -> bool:
    return (
        statement.start_code_point <= span.start_code_point
        and span.end_code_point_exclusive <= statement.end_code_point_exclusive
    )


def _validate_nested_span(span: TextSpan | None, statement: TextSpan, note_text: str, label: str) -> None:
    if span is None:
        return
    try:
        validate_text_span(span, note_text)
    except SpanValidationError as error:
        raise InvalidClaimSpanError(f"{label} is not a valid note span") from error
    if not _within_statement(span, statement):
        raise ClaimValidationError(f"{label} must be within statementSpan")


def _parse_claim(raw: object, context: NoteRevisionContext | Any, ordinal: int) -> Claim:
    if isinstance(raw, Claim):
        raw = raw.model_dump(by_alias=True)
    if not isinstance(raw, Mapping):
        raise ClaimValidationError("each provider claim must be an object")
    values = dict(raw)
    expected_revision = _context_value(context, "note_revision_id")
    expected_resident = _context_value(context, "resident_test_id")
    if "noteRevisionId" not in values and "note_revision_id" not in values:
        values["noteRevisionId"] = expected_revision
    if "residentTestId" not in values and "resident_test_id" not in values:
        values["residentTestId"] = expected_resident
    if "ordinal" not in values:
        values["ordinal"] = ordinal
    try:
        claim = Claim.model_validate(values)
    except (ValidationError, TypeError, ValueError) as error:
        raise ClaimValidationError("provider claim is schema-invalid") from error
    if claim.note_revision_id != expected_revision:
        raise ClaimValidationError("claim references a different note revision")
    if claim.resident_test_id != expected_resident:
        raise ClaimValidationError("claim references a different resident")
    note_text = _context_value(context, "note_body")
    try:
        validate_text_span(claim.statement_span, note_text)
    except SpanValidationError as error:
        raise InvalidClaimSpanError("statementSpan is not valid for the immutable note") from error
    _validate_nested_span(claim.negation_cue, claim.statement_span, note_text, "negationCue")
    _validate_nested_span(claim.certainty_cue, claim.statement_span, note_text, "certaintyCue")
    _validate_nested_span(claim.attribution_span, claim.statement_span, note_text, "attributionSpan")
    _validate_nested_span(claim.temporal_span, claim.statement_span, note_text, "temporalSpan")
    _validate_semantics(claim)
    for numeric in claim.numeric_values:
        _validate_numeric(numeric, claim.statement_span, note_text)
    return claim


def _validate_semantics(claim: Claim) -> None:
    statement = claim.statement_span.text
    folded = statement.casefold()
    if claim.polarity.value == "NEGATED":
        if claim.negation_cue is None or _NEGATION_PATTERN.search(claim.negation_cue.text) is None:
            raise ClaimValidationError("NEGATED claims require an explicit negation cue")
    elif _NEGATION_PATTERN.search(statement):
        raise ClaimValidationError("explicit negation cannot be represented as AFFIRMED")

    if claim.certainty.value == "CERTAIN" and _HEDGING_PATTERN.search(statement):
        raise ClaimValidationError("explicit hedging cannot be represented as CERTAIN")
    if claim.certainty.value in {"UNCERTAIN", "POSSIBLE"}:
        if claim.certainty_cue is None or (
            _HEDGING_PATTERN.search(claim.certainty_cue.text) is None
            and _APPROXIMATION_ONLY_PATTERN.search(claim.certainty_cue.text) is None
        ):
            raise ClaimValidationError("non-certain claims require an explicit uncertainty or approximation cue")

    if claim.attribution.value == "CARE_RECIPIENT":
        if claim.attribution_span is None or _CARE_RECIPIENT_PATTERN.search(claim.attribution_span.text) is None:
            raise ClaimValidationError("CARE_RECIPIENT attribution requires a resident-reported source cue")
    if claim.attribution.value == "CAREGIVER":
        if claim.attribution_span is None or _CAREGIVER_PATTERN.search(claim.attribution_span.text) is None:
            raise ClaimValidationError("CAREGIVER attribution requires a caregiver-observed source cue")

    if claim.medication is not None:
        for label, value in (
            ("medication.name", claim.medication.name),
            ("medication.doseRaw", claim.medication.dose_raw),
            ("medication.routeRaw", claim.medication.route_raw),
            ("medication.administrationTemporalText", claim.medication.administration_temporal_text),
        ):
            if value is not None and value.casefold() not in folded:
                raise ClaimValidationError(f"{label} must be directly stated within statementSpan")


def _validate_numeric(numeric: NumericValue, statement: TextSpan, note_text: str) -> None:
    try:
        validate_text_span(numeric.value_span, note_text)
    except SpanValidationError as error:
        raise InvalidClaimSpanError("numeric valueSpan is invalid") from error
    if not _within_statement(numeric.value_span, statement):
        raise ClaimValidationError("numeric valueSpan must be within statementSpan")
    if numeric.value_span.text != numeric.raw:
        raise ClaimValidationError("numeric raw must equal valueSpan.text")
    if _APPROXIMATION_PATTERN.search(numeric.raw) and not numeric.approximation:
        raise ClaimValidationError("an explicit approximation marker requires approximation=true")
    if numeric.approximation and not _APPROXIMATION_PATTERN.search(numeric.raw):
        raise ClaimValidationError("approximation=true requires an explicit approximation marker")
    if numeric.unit_span is not None:
        try:
            validate_text_span(numeric.unit_span, note_text)
        except SpanValidationError as error:
            raise InvalidClaimSpanError("numeric unitSpan is invalid") from error
        if not _within_statement(numeric.unit_span, statement):
            raise ClaimValidationError("numeric unitSpan must be within statementSpan")
        if numeric.unit_raw != numeric.unit_span.text:
            raise ClaimValidationError("unitRaw must equal unitSpan.text")
    if numeric.normalized_decimal is not None:
        match = _NUMBER_PATTERN.search(numeric.raw.replace(" ", ""))
        if match is None:
            raise ClaimValidationError("normalizedDecimal is not directly recoverable from raw")
        try:
            raw_decimal = Decimal(match.group(0).replace(",", "."))
        except InvalidOperation as error:
            raise ClaimValidationError("normalizedDecimal is invalid") from error
        if raw_decimal != numeric.normalized_decimal:
            raise ClaimValidationError("normalizedDecimal changes the raw numeric meaning")


def validate_claims(raw_claims: Sequence[object], context: NoteRevisionContext | Any) -> tuple[Claim, ...]:
    claims = tuple(_parse_claim(raw, context, index) for index, raw in enumerate(raw_claims, start=1))
    identifiers = [claim.id for claim in claims]
    if len(set(identifiers)) != len(identifiers):
        raise ClaimValidationError("claim ids must be unique within an extraction result")
    ordinals = [claim.ordinal for claim in claims]
    if len(set(ordinals)) != len(ordinals) or ordinals != list(range(1, len(ordinals) + 1)):
        raise ClaimValidationError("claim ordinals must be unique and ordered from one")
    return claims


class ClaimValidator:
    """Object facade around the pure validator for dependency injection."""

    def validate(self, raw_claims: Sequence[object], context: NoteRevisionContext | Any) -> tuple[Claim, ...]:
        return validate_claims(raw_claims, context)
