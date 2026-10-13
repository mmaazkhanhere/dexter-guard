from decimal import Decimal
import json
from pathlib import Path

from claim_extraction.models import NumericValue, TextSpan

from source_coverage.contracts import RelatedFindingRef, SourceSpan, UnresolvedSourceItem
from source_coverage.evaluation import evaluate_annotated_cases
from source_coverage.extraction import source_text_hash
from source_coverage.matching import HeuristicGermanSemanticMatcher, build_assessments
from tests.source_coverage.test_matching import claim, fact


def assess(source_fact, claims=(), *, unresolved=(), refs=None):
    relations = HeuristicGermanSemanticMatcher().match([source_fact], list(claims), run_id="acceptance-run")
    quotes = {source_fact.source_fact_id: (source_fact.fact_text,)}
    if unresolved:
        quotes.update({item.unresolved_source_item_id: ("Die Ursache ist unklar.",) for item in unresolved})
    return build_assessments([source_fact], unresolved, relations, source_quotes=quotes, related_refs=refs or {})


def measurement_fact(text="Temperatur 37,8 °C.", value="37.8"):
    return fact(text, category="MEASUREMENT", laterality="NONE", attribution="UNSPECIFIED", numeric_value=value, unit="CELSIUS", approximation="EXACT", documentation_expectation="REQUIRED", severity_policy_key="MEASUREMENT_OMISSION")


def numeric_claim(text, value, claim_id="claim-measurement"):
    value_start = text.index(value)
    unit_start = text.index("°")
    value_span = TextSpan(startCodePoint=value_start, endCodePointExclusive=value_start + len(value), startUtf16=value_start, endUtf16Exclusive=value_start + len(value), text=text[value_start:value_start + len(value)])
    unit_span = TextSpan(startCodePoint=unit_start, endCodePointExclusive=unit_start + 2, startUtf16=unit_start, endUtf16Exclusive=unit_start + 2, text=text[unit_start:unit_start + 2])
    numeric = NumericValue(raw=value, normalizedDecimal=Decimal(value.replace(",", ".")), unitRaw="°C", unitNormalized="CELSIUS", approximation=False, valueSpan=value_span, unitSpan=unit_span)
    return claim(text, claim_id=claim_id, category="VITAL_SIGN", subject="care_recipient", numeric_values=(numeric,))


def test_cov_001_all_expected_facts_covered():
    assessments, findings = assess(fact(), [claim("Bewohnerin berichtet über linksseitige Knieschmerzen.")])
    assert assessments[0].status.value == "COVERED" and findings == ()


def test_cov_002_missing_temperature_creates_measurement_finding():
    source = measurement_fact()
    assessments, findings = assess(source)
    assert assessments[0].status.value == "MISSING"
    assert findings[0].severity_policy_key == "MEASUREMENT_OMISSION"


def test_cov_003_lost_laterality_is_partial():
    assessments, findings = assess(fact(), [claim("Bewohnerin berichtet über Knieschmerzen.")])
    assert assessments[0].status.value == "PARTIALLY_COVERED"
    assert "LATERALITY" in {item.value for item in findings[0].missing_attributes}


def test_cov_004_german_paraphrase_is_covered_without_string_equality():
    source = fact()
    assessments, _ = assess(source, [claim("Bewohnerin berichtet über linksseitige Knieschmerzen.")])
    assert assessments[0].status.value == "COVERED"
    assert source.fact_text != "Bewohnerin berichtet über linksseitige Knieschmerzen."


def test_cov_005_omitted_negated_symptom_preserves_polarity():
    source = fact("Bewohnerin verneint Schwindel.", laterality="NONE", polarity="NEGATED")
    assessments, findings = assess(source)
    assert assessments[0].status.value == "MISSING"
    assert source.polarity.value == "NEGATED" and findings[0].requires_review is True


def test_cov_006_definite_rewrite_of_uncertainty_is_distorted():
    source = fact("Bewohnerin ist möglicherweise müde.", laterality="NONE", certainty="UNCERTAIN")
    assessments, findings = assess(source, [claim("Bewohnerin ist müde.")])
    assert assessments[0].status.value == "DISTORTED"
    assert "CERTAINTY" in {item.value for item in findings[0].distorted_attributes}


def test_cov_007_omission_finding_does_not_approve_or_mutate_note():
    source = fact("Bewohnerin berichtet über Schmerzen.", laterality="NONE")
    assessments, findings = assess(source)
    assert findings[0].requires_review is True
    assert not hasattr(findings[0], "approval") and not hasattr(findings[0], "note_text")
    assert assessments[0].source_quotes == (source.fact_text,)


def test_cov_008_revised_note_uses_new_run_boundary():
    from tests.source_coverage.test_service import make_service
    first_service, first_payload = make_service()
    first = first_service.execute(first_payload)
    second_service, second_payload = make_service(note_revision=2, run_id_prefix="coverage-revision-2")
    second = second_service.execute(second_payload)
    assert first.coverage_run_id != second.coverage_run_id
    assert first.note_revision == 1 and second.note_revision == 2


def test_cov_009_unresolved_source_is_uncertain_and_excluded_from_denominator():
    source = fact("Die Ursache ist unklar.", laterality="NONE")
    item = UnresolvedSourceItem(
        unresolvedSourceItemId="unresolved-1", sourceFactExtractionRunId="extract-1", sourceId="source-1", sourceVersion=1,
        residentContext=source.resident_context, sourceTextHash=source.source_text_hash, normalizationPolicy="NFC_CODEPOINTS",
        candidateSourceSpans=(SourceSpan(sourceId="source-1", sourceVersion=1, start=0, end=len(source.fact_text)),), explanation="The clause is explicitly unclear.",
    )
    assessments, findings = assess(source, unresolved=(item,))
    unresolved_assessment = assessments[-1]
    assert unresolved_assessment.status.value == "UNCERTAIN"
    assert unresolved_assessment.unresolved_source_item_id == "unresolved-1"
    assert findings[-1].documentation_expectation is None


def test_cov_010_incompatible_measurement_is_distorted_and_links_spec005():
    source = measurement_fact()
    related = {"fact-1": (RelatedFindingRef(owner="SPEC_005", findingId="NUM-001"), RelatedFindingRef(owner="SPEC_004", findingId="ev-1"))}
    assessments, findings = assess(source, [numeric_claim("Temperatur 38,8 °C.", "38,8")], refs=related)
    assert assessments[0].status.value == "DISTORTED"
    assert "NUMERIC_VALUE" in {item.value for item in findings[0].distorted_attributes}
    assert {item.owner for item in findings[0].related_finding_refs} == {"SPEC_004", "SPEC_005"}


def test_cov_011_faithful_duplicate_precedes_distorted_duplicate():
    source = measurement_fact()
    claims = [numeric_claim("Temperatur 37,8 °C.", "37,8", "faithful"), numeric_claim("Temperatur 38,8 °C.", "38,8", "distorted")]
    assessments, findings = assess(source, claims)
    assert assessments[0].status.value == "COVERED" and findings == ()


def test_evaluation_metrics_use_manual_annotations_and_report_raw_counts():
    report = evaluate_annotated_cases([
        {"caseId": "COV-001", "expected": "COVERED", "observed": "COVERED", "applicable": True},
        {"caseId": "COV-002", "expected": "MISSING", "observed": "MISSING", "applicable": True},
        {"caseId": "COV-009", "expected": "UNCERTAIN", "observed": "UNCERTAIN", "applicable": False},
    ])
    assert report["benchmarkCompleteness"] == 0.5
    assert report["omissionDetectionRecall"] == 1.0
    assert report["falseOmissionWarningRate"] == 0.0
    assert report["metricBasis"] == "MANUALLY_ANNOTATED_EXPECTED_FACTS"


def test_versioned_fixture_manifest_reproduces_published_raw_metrics():
    manifest = json.loads(Path("specs/006-source-coverage/fixtures/cov-001-010-v1.json").read_text(encoding="utf-8"))
    report = evaluate_annotated_cases(manifest["cases"])
    assert report["caseCount"] == 10
    assert report["applicableAnnotatedExpectedFacts"] == 9
    assert report["faithfullyCoveredAnnotatedExpectedFacts"] == 3
    assert report["correctlyFlaggedAnnotatedOmissions"] == 6
    assert report["falseOmissionWarnings"] == 0
