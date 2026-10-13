from human_review.context import EvidenceContextService


def test_context_rejects_negative_and_out_of_bounds_spans_without_highlights():
    context = EvidenceContextService(lambda source_id, version: ("abc", source_id, version))
    assert context.display("source-1", 1, [("source-1", 1, -1, 1)]).availability == "INVALID"
    assert context.display("source-1", 1, [("source-1", 1, 0, 4)]).availability == "INVALID"


def test_context_uses_unicode_code_point_offsets_for_evidence():
    context = EvidenceContextService(lambda source_id, version: ("Ärztin", source_id, version))
    result = context.display("source-1", 1, [("source-1", 1, 0, 6)])
    assert result.availability == "AVAILABLE"
    assert result.excerpts == ("Ärztin",)
