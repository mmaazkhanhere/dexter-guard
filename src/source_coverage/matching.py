"""Semantic relation validation and source-to-note coverage orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Protocol, Sequence

from claim_extraction.models import Claim, ClaimCategory, Certainty as ClaimCertainty, Polarity as ClaimPolarity

from .contracts import (
    Approximation,
    Attribution,
    Certainty,
    CoverageAssessment,
    CoverageFinding,
    CoverageStatus,
    MaterialAttribute,
    SemanticRelation,
    SemanticRelationKind,
    SourceFact,
    UnresolvedSourceItem,
)


class MatchingIntegrityError(ValueError):
    """Raised when a matcher result is incomplete or not closed over its inputs."""


class SemanticCoverageMatcher(Protocol):
    def match(self, facts: Sequence[SourceFact], claims: Sequence[Claim], *, run_id: str) -> tuple[SemanticRelation, ...]: ...


@dataclass(frozen=True)
class RelatedFinding:
    owner: str
    finding_id: str
    source_id: str
    source_version: int
    source_fact_id: str | None = None
    claim_id: str | None = None


_TOKEN_NORMALIZATION = {
    "schmerz": "pain", "schmerzen": "pain", "knieschmerzen": "pain knee", "knie": "knee",
    "schwindel": "dizziness", "übelkeit": "nausea", "uebelkeit": "nausea", "müde": "fatigue", "muede": "fatigue",
    "temperatur": "temperature", "fieber": "temperature", "gehen": "mobility", "läuft": "mobility", "laufen": "mobility",
    "hilfe": "assistance", "unterstützung": "assistance", "unterstuetzung": "assistance", "assistenz": "assistance",
    "gewaschen": "washed", "pflege": "care", "gelagert": "positioned", "verband": "dressing",
}


def _normalized_topics(text: str) -> set[str]:
    words = re.findall(r"[\wäöüÄÖÜß]+", text.casefold())
    topics: set[str] = set()
    for word in words:
        replacement = _TOKEN_NORMALIZATION.get(word)
        if replacement:
            topics.update(replacement.split())
        elif len(word) > 4 and word.endswith(("e", "en", "er", "es", "em")):
            topics.add(word.rstrip("e n r s m"))
        else:
            topics.add(word)
    return topics


def _infer_laterality(text: str) -> str:
    lower = text.casefold()
    left = any(token in lower for token in ("links", "linken", "linker", "linksseitig"))
    right = any(token in lower for token in ("rechts", "rechten", "rechter", "rechtsseitig"))
    if left and right:
        return "BILATERAL"
    if left:
        return "LEFT"
    if right:
        return "RIGHT"
    return "NONE"


def _claim_text(claim: Claim) -> str:
    return " ".join(part for part in (claim.claim_text, claim.subject, claim.predicate, claim.object) if part)


def _claim_numeric(claim: Claim) -> tuple[str | None, str | None, Approximation]:
    if not claim.numeric_values:
        return None, None, Approximation.UNKNOWN
    value = claim.numeric_values[0]
    normalized = str(value.normalized_decimal) if value.normalized_decimal is not None else value.raw.replace(",", ".")
    return normalized, value.unit_normalized, Approximation.APPROXIMATE if value.approximation else Approximation.EXACT


def _claim_attribution(claim: Claim) -> Attribution:
    if claim.attribution.value != "UNSPECIFIED":
        return Attribution[claim.attribution.value]
    text = _claim_text(claim).casefold()
    if re.search(r"\b(?:berichtet|klagte|gibt an|verneint|sagt)\b", text):
        return Attribution.CARE_RECIPIENT
    if re.search(r"\b(?:wirkte|beobachtet|zeigt|erscheint)\b", text):
        return Attribution.CAREGIVER
    return Attribution.UNSPECIFIED


def _claim_certainty(claim: Claim) -> Certainty:
    return Certainty[claim.certainty.value]


def _category_related(fact: SourceFact, claim: Claim) -> bool:
    categories = {
        "SYMPTOM": {ClaimCategory.SYMPTOM, ClaimCategory.OBSERVATION},
        "MEASUREMENT": {ClaimCategory.MEASUREMENT, ClaimCategory.VITAL_SIGN},
        "MOBILITY": {ClaimCategory.FUNCTION, ClaimCategory.OBSERVATION},
        "CARE_ACTION": {ClaimCategory.CARE_ACTION},
        "OBSERVATION": {ClaimCategory.OBSERVATION},
        "OTHER": {ClaimCategory.OTHER, ClaimCategory.OBSERVATION},
    }
    if claim.category in categories[fact.category.value]:
        return True
    fact_topics = _normalized_topics(fact.fact_text)
    claim_topics = _normalized_topics(_claim_text(claim))
    return len(fact_topics & claim_topics) >= 2


def _attribute_differences(fact: SourceFact, claim: Claim) -> tuple[tuple[MaterialAttribute, ...], tuple[MaterialAttribute, ...], tuple[MaterialAttribute, ...]]:
    preserved: list[MaterialAttribute] = []
    missing: list[MaterialAttribute] = []
    distorted: list[MaterialAttribute] = []

    def compare(attribute: MaterialAttribute, source_value: object, claim_value: object, *, absent_is_missing: bool = True) -> None:
        if source_value in (None, "", "UNKNOWN", "NONE"):
            return
        if claim_value in (None, "", "UNKNOWN", "NONE"):
            if absent_is_missing:
                missing.append(attribute)
            return
        if source_value == claim_value:
            preserved.append(attribute)
        else:
            distorted.append(attribute)

    claim_text = _claim_text(claim)
    claim_polarity = "NEGATED" if claim.polarity is ClaimPolarity.NEGATED else "AFFIRMED" if claim.polarity is ClaimPolarity.AFFIRMED else "UNKNOWN"
    compare(MaterialAttribute.POLARITY, fact.polarity.value, claim_polarity)
    compare(MaterialAttribute.CERTAINTY, fact.certainty.value, _claim_certainty(claim).value)
    compare(MaterialAttribute.ATTRIBUTION, fact.attribution.value, _claim_attribution(claim).value, absent_is_missing=False)
    compare(MaterialAttribute.TEMPORAL, fact.temporal_text, claim.temporal_text)
    compare(MaterialAttribute.LATERALITY, fact.laterality.value, _infer_laterality(claim_text))
    claim_numeric, claim_unit, claim_approximation = _claim_numeric(claim)
    compare(MaterialAttribute.NUMERIC_VALUE, fact.numeric_value, claim_numeric)
    compare(MaterialAttribute.UNIT, fact.unit, claim_unit)
    compare(MaterialAttribute.APPROXIMATION, fact.approximation.value, claim_approximation.value)
    if fact.mobility_assistance:
        if not any(token in claim_text.casefold() for token in ("hilfe", "unterstützung", "unterstuetzung", "assist", "rollator")):
            missing.append(MaterialAttribute.MOBILITY_ASSISTANCE)
        else:
            preserved.append(MaterialAttribute.MOBILITY_ASSISTANCE)
    if fact.care_action:
        if not (_normalized_topics(fact.care_action) & _normalized_topics(claim_text)):
            missing.append(MaterialAttribute.CARE_ACTION)
        else:
            preserved.append(MaterialAttribute.CARE_ACTION)
    if fact.subject:
        compare(MaterialAttribute.SUBJECT, fact.subject, claim.subject or ("care_recipient" if "bewohner" in claim_text.casefold() else None), absent_is_missing=True)
    return tuple(dict.fromkeys(preserved)), tuple(dict.fromkeys(missing)), tuple(dict.fromkeys(distorted))


class HeuristicGermanSemanticMatcher:
    """Deterministic semantic baseline; a model adapter can implement the same port."""

    matcher_version = "heuristic-semantic-v1"

    def match(self, facts: Sequence[SourceFact], claims: Sequence[Claim], *, run_id: str) -> tuple[SemanticRelation, ...]:
        relations: list[SemanticRelation] = []
        for fact in facts:
            for claim in claims:
                if not _category_related(fact, claim):
                    continue
                preserved, missing, distorted = _attribute_differences(fact, claim)
                if distorted:
                    kind = SemanticRelationKind.RELATED_ATTRIBUTE_DISTORTED
                    explanation = "A related claim changes material source attributes."
                elif missing:
                    kind = SemanticRelationKind.RELATED_ATTRIBUTE_OMITTED
                    explanation = "A related claim omits material source attributes."
                else:
                    kind = SemanticRelationKind.FAITHFUL
                    explanation = "The claim preserves the source fact and its material attributes."
                relations.append(SemanticRelation(
                    sourceFactId=fact.source_fact_id, claimId=claim.id, kind=kind,
                    preservedAttributes=preserved, missingAttributes=missing, distortedAttributes=distorted,
                    explanation=explanation,
                ))
        return tuple(relations)


def validate_relations(relations: Iterable[SemanticRelation], facts: Sequence[SourceFact], claims: Sequence[Claim]) -> tuple[SemanticRelation, ...]:
    fact_ids = {fact.source_fact_id for fact in facts}
    claim_ids = {claim.id for claim in claims}
    result = tuple(relations)
    for relation in result:
        if relation.source_fact_id not in fact_ids or (relation.claim_id is not None and relation.claim_id not in claim_ids):
            raise MatchingIntegrityError("semantic relation is not closed over the requested immutable inputs")
    return result


def _status_for(relations: Sequence[SemanticRelation]) -> tuple[CoverageStatus, tuple[str, ...], tuple[MaterialAttribute, ...], tuple[MaterialAttribute, ...], tuple[MaterialAttribute, ...], str]:
    faithful = [item for item in relations if item.kind is SemanticRelationKind.FAITHFUL]
    if faithful:
        item = faithful[0]
        return CoverageStatus.COVERED, (item.claim_id,), item.preserved_attributes, (), (), item.explanation
    distorted = [item for item in relations if item.kind is SemanticRelationKind.RELATED_ATTRIBUTE_DISTORTED]
    if distorted:
        item = distorted[0]
        return CoverageStatus.DISTORTED, tuple(item.claim_id for item in distorted if item.claim_id), item.preserved_attributes, (), tuple(dict.fromkeys(a for item in distorted for a in item.distorted_attributes)), "A related claim changes material source meaning."
    partial = [item for item in relations if item.kind is SemanticRelationKind.RELATED_ATTRIBUTE_OMITTED]
    if partial:
        item = partial[0]
        return CoverageStatus.PARTIALLY_COVERED, tuple(item.claim_id for item in partial if item.claim_id), item.preserved_attributes, tuple(dict.fromkeys(a for item in partial for a in item.missing_attributes)), (), "A related claim omits material source detail."
    if any(item.kind is SemanticRelationKind.UNRESOLVED for item in relations):
        return CoverageStatus.UNCERTAIN, tuple(item.claim_id for item in relations if item.claim_id), (), (), (), "Semantic comparison could not be resolved reliably."
    return CoverageStatus.MISSING, (), (), (), (), "No related candidate claim was found."


def build_assessments(
    facts: Sequence[SourceFact],
    unresolved_items: Sequence[UnresolvedSourceItem],
    relations: Sequence[SemanticRelation],
    *,
    source_quotes: Mapping[str, tuple[str, ...]],
    related_refs: Mapping[str, tuple[object, ...]] | None = None,
) -> tuple[tuple[CoverageAssessment, ...], tuple[CoverageFinding, ...]]:
    related_refs = related_refs or {}
    assessments: list[CoverageAssessment] = []
    findings: list[CoverageFinding] = []
    by_fact: dict[str, list[SemanticRelation]] = {}
    for relation in relations:
        by_fact.setdefault(relation.source_fact_id, []).append(relation)
    for index, fact in enumerate(facts, start=1):
        status, claims, preserved, missing, distorted, explanation = _status_for(by_fact.get(fact.source_fact_id, ()))
        assessment_id = f"assessment-{index}"
        refs = tuple(related_refs.get(fact.source_fact_id, ()))
        assessment = CoverageAssessment(
            assessmentId=assessment_id, sourceFactId=fact.source_fact_id, unresolvedSourceItemId=None,
            status=status, sourceSpans=fact.source_spans, sourceQuotes=source_quotes[fact.source_fact_id],
            matchedClaimIds=claims, preservedAttributes=preserved, missingAttributes=missing,
            distortedAttributes=distorted, explanation=explanation, relatedFindingRefs=refs,
        )
        assessments.append(assessment)
        if status is not CoverageStatus.COVERED:
            findings.append(CoverageFinding(
                coverageFindingId=f"finding-{index}", assessmentId=assessment_id, sourceFactId=fact.source_fact_id,
                unresolvedSourceItemId=None, status=status, coverageStatusPolicyVersion="COVERAGE_STATUS-v1",
                expectationPolicyVersion="COVERAGE_EXPECTATION-v1", rulesetVersion="COVERAGE-RULESET-v1",
                documentationExpectation=fact.documentation_expectation, severityPolicyKey=fact.severity_policy_key,
                sourceSpans=fact.source_spans, sourceQuotes=source_quotes[fact.source_fact_id], matchedClaimIds=claims,
                missingAttributes=missing, distortedAttributes=distorted,
                suggestion=f"Prüfen und gegebenenfalls quellengetreu dokumentieren: {source_quotes[fact.source_fact_id][0]}",
                relatedFindingRefs=refs, requiresReview=True,
            ))
    for offset, item in enumerate(unresolved_items, start=len(assessments) + 1):
        assessment_id = f"assessment-{offset}"
        refs = tuple(related_refs.get(item.unresolved_source_item_id, ()))
        assessment = CoverageAssessment(
            assessmentId=assessment_id, sourceFactId=None, unresolvedSourceItemId=item.unresolved_source_item_id,
            status=CoverageStatus.UNCERTAIN, sourceSpans=item.candidate_source_spans,
            sourceQuotes=source_quotes[item.unresolved_source_item_id], matchedClaimIds=(), preservedAttributes=(),
            missingAttributes=(), distortedAttributes=(), explanation=item.explanation, relatedFindingRefs=refs,
        )
        assessments.append(assessment)
        findings.append(CoverageFinding(
            coverageFindingId=f"finding-{offset}", assessmentId=assessment_id, sourceFactId=None,
            unresolvedSourceItemId=item.unresolved_source_item_id, status=CoverageStatus.UNCERTAIN,
            coverageStatusPolicyVersion="COVERAGE_STATUS-v1", expectationPolicyVersion="COVERAGE_EXPECTATION-v1",
            rulesetVersion="COVERAGE-RULESET-v1", documentationExpectation=None, severityPolicyKey=None,
            sourceSpans=item.candidate_source_spans, sourceQuotes=source_quotes[item.unresolved_source_item_id],
            matchedClaimIds=(), missingAttributes=(), distortedAttributes=(),
            suggestion="Quellenaussage manuell prüfen; es wird keine nicht belegte Tatsache behauptet.",
            relatedFindingRefs=refs, requiresReview=True,
        ))
    return tuple(assessments), tuple(findings)


def correlate_findings(fact_or_item_id: str, related: Iterable[RelatedFinding]) -> tuple[dict[str, str], ...]:
    """Return only stable Spec 004/005 references; outcomes are never recomputed."""
    return tuple({"owner": item.owner, "findingId": item.finding_id} for item in related if item.source_fact_id == fact_or_item_id or item.claim_id == fact_or_item_id)
