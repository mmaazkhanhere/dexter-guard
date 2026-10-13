from datetime import datetime, timezone

import pytest

from human_review.context import EvidenceContextService
from human_review.contracts import SuggestedCorrection
from human_review.service import ReviewService
from human_review.repository import InMemoryReviewRepository
from human_review.approval import ReviewServiceError


def test_evidence_highlight_is_derived_only_from_exact_source_version():
    context = EvidenceContextService(lambda source_id, version: ("Die Temperatur ist 37,2 Grad.", "source-1", 1))
    available = context.display("source-1", 1, [("source-1", 1, 4, 14)])
    assert available.availability == "AVAILABLE"
    assert available.excerpts == ("Temperatur",)
    invalid = context.display("source-1", 1, [("source-1", 2, 4, 15)])
    assert invalid.availability == "INVALID"
    assert invalid.spans == ()


def test_missing_evidence_is_not_rendered_as_contradiction():
    context = EvidenceContextService(lambda source_id, version: ("Text", source_id, version))
    result = context.display("source-1", 1, [])
    assert result.availability == "MISSING"
    assert result.excerpts == ()


def test_unusable_suggestion_cannot_create_successor_revision():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Die Temperatur ist 37,2 Grad.")
    suggestion = SuggestedCorrection(
        suggestionId="suggestion-1", findingId="finding-1", noteId="note-1", baseRevision=1,
        replacement="Fieber", targetNoteSpan={"startCodePoint": 4, "endCodePointExclusive": 14, "text": "Temperatur"},
        supportStatus="UNUSABLE", supportSpans=(), generatedBy="SPEC_007_CORRECTION_ADAPTER", createdAt=datetime.now(timezone.utc),
    )
    service.add_suggestion(suggestion)
    with pytest.raises(ReviewServiceError, match="SUGGESTION_NOT_USABLE"):
        service.accept_suggestion("note-1", suggestion_id="suggestion-1", expected_revision=1, reviewer_label="r")


def test_usable_suggestion_creates_one_successor_revision():
    service = ReviewService(InMemoryReviewRepository())
    service.seed_note("note-1", "source-1", 1, "Die Temperatur ist 37,2 Grad.")
    suggestion = SuggestedCorrection(
        suggestionId="suggestion-1", findingId="finding-1", noteId="note-1", baseRevision=1,
        replacement="Temperaturmessung", targetNoteSpan={"startCodePoint": 4, "endCodePointExclusive": 14, "text": "Temperatur"},
        supportStatus="USABLE", supportSpans=({"sourceId": "source-1", "sourceVersion": 1, "start": 4, "end": 14},), generatedBy="REVIEWER", createdAt=datetime.now(timezone.utc),
    )
    service.add_suggestion(suggestion)
    successor = service.accept_suggestion("note-1", suggestion_id="suggestion-1", expected_revision=1, reviewer_label="r")
    assert successor.revision == 2
    assert successor.content == "Die Temperaturmessung ist 37,2 Grad."
