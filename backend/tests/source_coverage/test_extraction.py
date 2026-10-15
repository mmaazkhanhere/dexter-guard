from datetime import datetime, timezone

import pytest

from source_ingestion.contracts import SourceDocument
from source_coverage.contracts import SourceSpan
from source_coverage.extraction import (
    ExtractionIntegrityError,
    HeuristicGermanSourceFactExtractor,
    NORMALIZATION_POLICY,
    SourceFactExtractionResult,
    source_text_hash,
    validate_source_span,
)


def source(text: str) -> SourceDocument:
    return SourceDocument(
        source_id="source-1", source_version=1, resident_test_id="resident-1", language="de-DE",
        transcript_text=text, created_at=datetime.now(timezone.utc),
    )


def test_extractor_splits_atomic_german_facts_and_preserves_attributes():
    text = "Frau Müller klagte über Schmerzen im linken Knie. Temperatur ca. 37,8 °C um 08:00 Uhr. Schwindel verneint. Die Bewohnerin kann nur mit Hilfe gehen und wurde gewaschen."
    result = HeuristicGermanSourceFactExtractor().extract(source(text), extraction_run_id="extract-1")
    assert {fact.category.value for fact in result.facts} >= {"SYMPTOM", "MEASUREMENT", "MOBILITY", "CARE_ACTION"}
    pain = next(item for item in result.facts if item.category.value == "SYMPTOM" and "Schmerzen" in item.fact_text)
    assert pain.polarity.value == "AFFIRMED"
    assert pain.laterality.value == "LEFT"
    measurement = next(item for item in result.facts if item.category.value == "MEASUREMENT")
    assert measurement.approximation.value == "APPROXIMATE"
    assert measurement.temporal_text == "um 08:00 Uhr"
    negated = next(item for item in result.facts if "Schwindel" in item.fact_text)
    assert negated.polarity.value == "NEGATED"
    assert all(text[item.source_spans[0].start:item.source_spans[0].end] == item.fact_text for item in result.facts)


def test_unresolved_source_clause_is_source_linked_and_not_a_fact():
    result = HeuristicGermanSourceFactExtractor().extract(source("Die Ursache ist unklar."), extraction_run_id="extract-2")
    assert result.facts == ()
    assert len(result.unresolved_items) == 1
    assert result.unresolved_items[0].candidate_source_spans[0].start == 0


def test_multiple_fact_categories_from_one_clause_receive_unique_ids():
    result = HeuristicGermanSourceFactExtractor().extract(
        source("Die Bewohnerin hatte Schwindel beim Aufstehen mit dem Rollator."),
        extraction_run_id="extract-duplicate-id",
    )

    assert {fact.category.value for fact in result.facts} >= {"SYMPTOM", "MOBILITY"}
    assert len({fact.source_fact_id for fact in result.facts}) == len(result.facts)


def test_span_validation_uses_exact_unicode_codepoint_offsets():
    document = source("Ärger 😊 é")
    span = SourceSpan(sourceId="source-1", sourceVersion=1, start=0, end=len(document.transcript_text))
    assert validate_source_span(span, document) == document.transcript_text
    with pytest.raises(ExtractionIntegrityError):
        validate_source_span(SourceSpan(sourceId="source-1", sourceVersion=2, start=0, end=1), document)
    with pytest.raises(ExtractionIntegrityError):
        validate_source_span(SourceSpan(sourceId="source-1", sourceVersion=1, start=0, end=len(document.transcript_text) + 1), document)


def test_stale_hash_is_rejected():
    document = source("Schmerzen.")
    result = SourceFactExtractionResult(
        extraction_run_id="extract-3", source_id="source-1", source_version=1,
        source_text_hash="0" * 64, normalization_policy=NORMALIZATION_POLICY, facts=(), unresolved_items=(),
    )
    from source_coverage.extraction import validate_extraction_result
    with pytest.raises(ExtractionIntegrityError):
        validate_extraction_result(result, document)
