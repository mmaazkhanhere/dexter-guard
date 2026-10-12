from datetime import datetime, timezone
from decimal import Decimal

from claim_extraction.models import Claim
from source_ingestion.contracts import SourceDocument

from source_coverage.contracts import SemanticRelation, SourceFact, SourceSpan
from source_coverage.extraction import source_text_hash
from source_coverage.matching import HeuristicGermanSemanticMatcher, build_assessments


def claim(text: str, *, claim_id: str = "claim-1", category: str = "SYMPTOM", polarity: str = "AFFIRMED", certainty: str = "CERTAIN", subject: str | None = "care_recipient", numeric_values=(), temporal_text: str | None = None) -> Claim:
    return Claim(
        id=claim_id, noteRevisionId="note-1:r1", residentTestId="resident-1", ordinal=1,
        category=category, statementSpan={"startCodePoint": 0, "endCodePointExclusive": len(text), "startUtf16": 0, "endUtf16Exclusive": len(text), "text": text},
        claimText=text, subject=subject, predicate=None, object=None, polarity=polarity,
        negationCue={"startCodePoint": 0, "endCodePointExclusive": 4, "startUtf16": 0, "endUtf16Exclusive": 4, "text": text[:4]} if polarity == "NEGATED" else None,
        certainty=certainty, certaintyCue={"startCodePoint": 0, "endCodePointExclusive": 1, "startUtf16": 0, "endUtf16Exclusive": 1, "text": text[:1]} if certainty in {"UNCERTAIN", "POSSIBLE"} else None,
        attribution="UNSPECIFIED", numericValues=numeric_values, extractionWarnings=(), temporalText=temporal_text,
        temporalSpan={"startCodePoint": 0, "endCodePointExclusive": len(temporal_text), "startUtf16": 0, "endUtf16Exclusive": len(temporal_text), "text": temporal_text} if temporal_text else None,
    )


def fact(text: str = "Frau Müller klagte über Schmerzen im linken Knie.", **kwargs) -> SourceFact:
    return SourceFact(
        sourceFactId="fact-1", sourceFactExtractionRunId="extract-1", sourceId="source-1", sourceVersion=1,
        residentContext={"residentTestId": "resident-1", "source": "SPEC_001_SOURCE_DOCUMENT", "trustLevel": "AUTHORITATIVE_TRANSCRIPT", "version": "source-1:v1", "permittedUse": "TRANSCRIPT_EVIDENCE_ONLY"},
        sourceTextHash=source_text_hash(text), normalizationPolicy="NFC_CODEPOINTS", category=kwargs.get("category", "SYMPTOM"), factText=text,
        subject=kwargs.get("subject", "care_recipient"), polarity=kwargs.get("polarity", "AFFIRMED"), certainty=kwargs.get("certainty", "CERTAIN"), attribution=kwargs.get("attribution", "CARE_RECIPIENT"),
        temporalText=kwargs.get("temporal_text"), laterality=kwargs.get("laterality", "LEFT"), numericValue=kwargs.get("numeric_value"), unit=kwargs.get("unit"), approximation=kwargs.get("approximation", "UNKNOWN"),
        mobilityAssistance=kwargs.get("mobility_assistance"), careAction=kwargs.get("care_action"), documentationExpectation=kwargs.get("documentation_expectation", "IMPORTANT"), severityPolicyKey=kwargs.get("severity_policy_key", "SYMPTOM_OMISSION"),
        sourceSpans=(SourceSpan(sourceId="source-1", sourceVersion=1, start=0, end=len(text)),),
    )


def test_german_paraphrase_is_covered():
    relations = HeuristicGermanSemanticMatcher().match([fact()], [claim("Bewohnerin berichtet über linksseitige Knieschmerzen.")], run_id="run-1")
    assessments, findings = build_assessments([fact()], (), relations, source_quotes={"fact-1": (fact().fact_text,)})
    assert assessments[0].status.value == "COVERED"
    assert findings == ()


def test_lost_laterality_is_partially_covered():
    source = fact()
    relations = HeuristicGermanSemanticMatcher().match([source], [claim("Bewohnerin berichtet über Knieschmerzen.")], run_id="run-1")
    assessments, findings = build_assessments([source], (), relations, source_quotes={"fact-1": (source.fact_text,)})
    assert assessments[0].status.value == "PARTIALLY_COVERED"
    assert "LATERALITY" in {item.value for item in findings[0].missing_attributes}


def test_lost_negation_and_uncertainty_are_distorted():
    negated = fact("Bewohnerin verneint Schwindel.", laterality="NONE", polarity="NEGATED")
    negated_claim = claim("Bewohnerin hat Schwindel.", polarity="AFFIRMED")
    relations = HeuristicGermanSemanticMatcher().match([negated], [negated_claim], run_id="run-1")
    assert relations[0].kind.value == "RELATED_ATTRIBUTE_DISTORTED"
    uncertain = fact("Bewohnerin ist möglicherweise müde.", laterality="NONE", certainty="UNCERTAIN")
    certain_claim = claim("Bewohnerin ist müde.", certainty="CERTAIN")
    assert HeuristicGermanSemanticMatcher().match([uncertain], [certain_claim], run_id="run-1")[0].kind.value == "RELATED_ATTRIBUTE_DISTORTED"


def test_faithful_duplicate_has_coverage_precedence_over_distortion():
    source = fact()
    claims = [claim("Bewohnerin berichtet über linksseitige Knieschmerzen.", claim_id="faithful"), claim("Bewohnerin berichtet über rechtsseitige Knieschmerzen.", claim_id="distorted")]
    relations = HeuristicGermanSemanticMatcher().match([source], claims, run_id="run-1")
    assessments, findings = build_assessments([source], (), relations, source_quotes={"fact-1": (source.fact_text,)})
    assert assessments[0].status.value == "COVERED"
    assert findings == ()


def test_unresolved_semantic_relation_is_uncertain_even_with_a_related_relation():
    source = fact()
    relations = (
        SemanticRelation(sourceFactId="fact-1", claimId="claim-1", kind="UNRESOLVED", preservedAttributes=(), missingAttributes=(), distortedAttributes=(), explanation="Ambiguous semantic match."),
        SemanticRelation(sourceFactId="fact-1", claimId="claim-2", kind="FAITHFUL", preservedAttributes=(), missingAttributes=(), distortedAttributes=(), explanation="Faithful candidate."),
    )
    assessments, findings = build_assessments([source], (), relations, source_quotes={"fact-1": (source.fact_text,)})
    assert assessments[0].status.value == "UNCERTAIN"
    assert findings[0].requires_review is True
