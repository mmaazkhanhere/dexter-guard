from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from source_coverage.contracts import (
    Approximation,
    CoverageAssessment,
    CoverageCounts,
    CoverageStatus,
    DocumentationExpectation,
    MaterialAttribute,
    ResidentContextReference,
    SourceFact,
    SourceFactCategory,
    SourceSpan,
    UnresolvedSourceItem,
)
from source_coverage.policy import expectation_for


def span() -> SourceSpan:
    return SourceSpan(sourceId="source-1", sourceVersion=1, start=0, end=5)


def context() -> ResidentContextReference:
    return ResidentContextReference(
        residentTestId="resident-1", source="SPEC_001_SOURCE_DOCUMENT",
        trustLevel="AUTHORITATIVE_TRANSCRIPT", version="v1", permittedUse="TRANSCRIPT_EVIDENCE_ONLY",
    )


def fact(**overrides) -> SourceFact:
    payload = dict(
        sourceFactId="fact-1", sourceFactExtractionRunId="extract-1", sourceId="source-1", sourceVersion=1,
        residentContext=context(), sourceTextHash="a" * 64, normalizationPolicy="NFC_CODEPOINTS",
        category=SourceFactCategory.SYMPTOM, factText="Schmerzen", subject="resident-1",
        polarity="AFFIRMED", certainty="CERTAIN", attribution="CARE_RECIPIENT", laterality="NONE",
        approximation=Approximation.UNKNOWN, documentationExpectation="IMPORTANT", severityPolicyKey="SYMPTOM_OMISSION",
        sourceSpans=(span(),),
    )
    payload.update(overrides)
    return SourceFact(**payload)


def test_source_fact_rejects_contextual_severity_and_cross_version_span():
    with pytest.raises(ValidationError):
        fact(documentationExpectation=DocumentationExpectation.CONTEXTUAL, severityPolicyKey=None, sourceSpans=(SourceSpan(sourceId="other", sourceVersion=1, start=0, end=2),))


def test_unresolved_item_is_source_linked_but_has_no_asserted_fact():
    item = UnresolvedSourceItem(
        unresolvedSourceItemId="unresolved-1", sourceFactExtractionRunId="extract-1", sourceId="source-1", sourceVersion=1,
        residentContext=context(), sourceTextHash="a" * 64, normalizationPolicy="NFC_CODEPOINTS",
        candidateSourceSpans=(span(),), explanation="The clause boundary is ambiguous.",
    )
    assert item.candidate_source_spans[0].start == 0


def test_assessment_closure_rejects_covered_without_claim():
    with pytest.raises(ValidationError):
        CoverageAssessment(
            assessmentId="assessment-1", sourceFactId="fact-1", unresolvedSourceItemId=None,
            status=CoverageStatus.COVERED, sourceSpans=(span(),), sourceQuotes=("Schmerz",),
            matchedClaimIds=(), preservedAttributes=(), missingAttributes=(), distortedAttributes=(),
            explanation="No claim.", relatedFindingRefs=(),
        )


def test_runtime_counts_use_null_for_zero_denominator():
    counts = CoverageCounts(
        extractedExpectedFacts=0, coveredExpectedFacts=0, partiallyCoveredExpectedFacts=0,
        missingExpectedFacts=0, distortedExpectedFacts=0, uncertainExpectedFacts=0,
        unresolvedSourceItems=1, unresolvedSourceItemsRequireReview=True,
        runtimeCompleteness=None, metricBasis="SYSTEM_EXTRACTED_EXPECTED_FACTS",
    )
    assert counts.runtime_completeness is None


def test_expectation_policy_is_deterministic_and_has_no_final_severity():
    expectation, key = expectation_for(SourceFactCategory.MEASUREMENT)
    assert expectation is DocumentationExpectation.REQUIRED
    assert key == "MEASUREMENT_OMISSION"
