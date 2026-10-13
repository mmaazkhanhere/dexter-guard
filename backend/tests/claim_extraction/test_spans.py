import pytest

from claim_extraction.models import TextSpan
from claim_extraction.spans import SpanValidationError, make_text_span, validate_text_span


def test_unicode_span_validates_code_points_and_utf16_coordinates() -> None:
    note = "Bewohnerin 😊 ist wach."
    start = note.index("😊")
    text_span = make_text_span(note, start, start + 1)

    assert text_span.text == "😊"
    assert text_span.start_code_point == start
    assert text_span.end_code_point_exclusive == start + 1
    assert text_span.end_utf16_exclusive - text_span.start_utf16 == 2
    validate_text_span(text_span, note)


def test_decimal_comma_span_and_overlapping_spans_are_valid() -> None:
    note = "Temperatur etwa 37,8 °C."
    statement = make_text_span(note, 0, len(note) - 1)
    value = make_text_span(note, note.index("37,8"), note.index("37,8") + 4)
    overlapping = make_text_span(note, note.index("etwa"), note.index("°C") + 2)

    validate_text_span(statement, note)
    validate_text_span(value, note)
    validate_text_span(overlapping, note)


@pytest.mark.parametrize(
    "span",
    [
        {"startCodePoint": -1, "endCodePointExclusive": 2, "startUtf16": 0, "endUtf16Exclusive": 2, "text": "x"},
        {"startCodePoint": 0, "endCodePointExclusive": 99, "startUtf16": 0, "endUtf16Exclusive": 99, "text": "x"},
        {"startCodePoint": 2, "endCodePointExclusive": 1, "startUtf16": 2, "endUtf16Exclusive": 1, "text": "x"},
    ],
)
def test_invalid_offsets_are_rejected(span: dict[str, object]) -> None:
    with pytest.raises(Exception):
        validate_text_span(TextSpan.model_validate(span), "x")


def test_mismatched_text_and_utf16_coordinates_are_rejected() -> None:
    note = "A 😊 B"
    valid = make_text_span(note, 2, 3)
    with pytest.raises(SpanValidationError):
        validate_text_span(valid.model_copy(update={"text": "B"}), note)
    with pytest.raises(SpanValidationError):
        validate_text_span(valid.model_copy(update={"start_utf16": 1}), note)
