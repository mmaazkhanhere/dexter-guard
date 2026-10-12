from __future__ import annotations

import pytest

from evidence_verification.spans import SourceSpanValidationError, SourceTextIndex


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("Ärztin sagt: keine Schmerzen.", "keine Schmerzen"),
        ("Cafe\u0301 ist geöffnet.", "Cafe\u0301"),
        ("Visite 👩🏽‍⚕️: stabil.", "👩🏽‍⚕️"),
        ("  Zeile eins\nZeile zwei  ", "Zeile eins\nZeile zwei"),
        ("Satz:; (kontext).", "; (kontext)"),
    ],
)
def test_index_derives_exact_code_point_substrings(text: str, fragment: str) -> None:
    index = SourceTextIndex(text)
    start = text.index(fragment)
    end = start + len(fragment)

    assert index.length == len(text)
    assert index.derive(start, end) == fragment
    assert index.matches(start, end, fragment)


@pytest.mark.parametrize(
    ("start", "end"),
    [(-1, 1), (1, 1), (2, 1), (0, 100), (0, 0)],
)
def test_index_rejects_empty_reversed_and_out_of_bounds_ranges(start: int, end: int) -> None:
    with pytest.raises(SourceSpanValidationError):
        SourceTextIndex("abc").derive(start, end)


def test_index_does_not_accept_boolean_offsets() -> None:
    with pytest.raises(SourceSpanValidationError):
        SourceTextIndex("abc").validate(True, 2)


def test_index_preserves_combining_and_non_bmp_code_point_boundaries() -> None:
    text = "e\u0301 👩🏽‍⚕️"
    index = SourceTextIndex(text)
    assert index.derive(0, 2) == "e\u0301"
    emoji_start = text.index("👩")
    assert index.derive(emoji_start, emoji_start + len("👩🏽‍⚕️")) == "👩🏽‍⚕️"

