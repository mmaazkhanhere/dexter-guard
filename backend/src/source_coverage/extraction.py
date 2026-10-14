"""Source-fact extraction ports and deterministic integrity validation."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from source_ingestion.contracts import SourceDocument

from .contracts import (
    Approximation,
    Attribution,
    Certainty,
    Laterality,
    Polarity,
    ResidentContextReference,
    SourceFact,
    SourceFactCategory,
    SourceSpan,
    UnresolvedSourceItem,
)
from .policy import expectation_for


NORMALIZATION_POLICY = "NFC_CODEPOINTS"


class ExtractionIntegrityError(ValueError):
    """Raised when an extraction result cannot be tied to immutable source text."""


@dataclass(frozen=True)
class SourceFactExtractionResult:
    extraction_run_id: str
    source_id: str
    source_version: int
    source_text_hash: str
    normalization_policy: str
    facts: tuple[SourceFact, ...]
    unresolved_items: tuple[UnresolvedSourceItem, ...]
    provider_version: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    extracted_at: datetime = datetime.now(timezone.utc)


class SourceFactExtractor(Protocol):
    def extract(self, source: SourceDocument, *, extraction_run_id: str | None = None) -> SourceFactExtractionResult: ...


def source_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _context(source: SourceDocument) -> ResidentContextReference:
    return ResidentContextReference(
        residentTestId=source.resident_test_id,
        source="SPEC_001_SOURCE_DOCUMENT",
        trustLevel="AUTHORITATIVE_TRANSCRIPT",
        version=f"{source.source_id}:v{source.source_version}",
        permittedUse="TRANSCRIPT_EVIDENCE_ONLY",
    )


def validate_source_span(span: SourceSpan, source: SourceDocument) -> str:
    if (span.source_id, span.source_version) != (source.source_id, source.source_version):
        raise ExtractionIntegrityError("source span identity does not match the requested immutable source")
    if span.end > len(source.transcript_text):
        raise ExtractionIntegrityError("source span exceeds immutable transcript length")
    excerpt = source.transcript_text[span.start : span.end]
    if not excerpt:
        raise ExtractionIntegrityError("source span must resolve to non-empty text")
    return excerpt


def validate_extraction_result(result: SourceFactExtractionResult, source: SourceDocument) -> None:
    if (result.source_id, result.source_version) != (source.source_id, source.source_version):
        raise ExtractionIntegrityError("extraction source identity does not match the requested source")
    if result.source_text_hash != source_text_hash(source.transcript_text):
        raise ExtractionIntegrityError("extraction source text hash is stale")
    if result.normalization_policy != NORMALIZATION_POLICY:
        raise ExtractionIntegrityError("unsupported source normalization policy")
    seen: set[str] = set()
    for fact in result.facts:
        if fact.source_fact_id in seen:
            raise ExtractionIntegrityError("duplicate source fact ID")
        seen.add(fact.source_fact_id)
        if fact.source_fact_extraction_run_id != result.extraction_run_id:
            raise ExtractionIntegrityError("source fact belongs to another extraction run")
        if fact.source_text_hash != result.source_text_hash or fact.normalization_policy != result.normalization_policy:
            raise ExtractionIntegrityError("source fact provenance metadata mismatch")
        if fact.resident_context != _context(source):
            raise ExtractionIntegrityError("source fact resident context mismatch")
        excerpts = [validate_source_span(span, source) for span in fact.source_spans]
        if fact.fact_text not in excerpts and fact.fact_text != " ".join(excerpts):
            raise ExtractionIntegrityError("source fact text is not derived from its evidence spans")
    for item in result.unresolved_items:
        if item.unresolved_source_item_id in seen:
            raise ExtractionIntegrityError("duplicate unresolved source item ID")
        seen.add(item.unresolved_source_item_id)
        if item.source_fact_extraction_run_id != result.extraction_run_id:
            raise ExtractionIntegrityError("unresolved item belongs to another extraction run")
        if item.source_text_hash != result.source_text_hash or item.normalization_policy != result.normalization_policy:
            raise ExtractionIntegrityError("unresolved item provenance metadata mismatch")
        if item.resident_context != _context(source):
            raise ExtractionIntegrityError("unresolved item resident context mismatch")
        for span in item.candidate_source_spans:
            validate_source_span(span, source)


_CLAUSE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])|\s*;\s*|\s+und\s+(?=(?:die |der |das |es |sie |er |wurde |wurden |kann |benötigt))", re.IGNORECASE)
_MEASUREMENT = re.compile(
    r"(?:(?:temperatur|fieber)\s*(?:(?:von|betr\u00e4gt)\s*)?|(?:puls|herzfrequenz)\s*(?:(?:liegt\s+)?bei\s*)?)"
    r"(?P<approximation>ca\.\s*)?(?P<value>-?\d+(?:[,.]\d+)?)\s*"
    r"(?P<unit>\u00b0?c|grad|\u00b0celsius|celsius|bpm|schl(?:\u00e4|ae)ge[n]?\s+pro\s+minute)",
    re.IGNORECASE,
)
_TIME = re.compile(r"\b(?:um|gegen)\s+(\d{1,2}:\d{2})\s*uhr\b|\b(heute|gestern|morgen|seit\s+[^,.!?]+)", re.IGNORECASE)
_LEFT = re.compile(r"\b(?:links(?:seitig(?:e|en|em)?)?|linken?|linker)\b", re.IGNORECASE)
_RIGHT = re.compile(r"\b(?:rechts(?:seitig(?:e|en|em)?)?|rechten?|rechter)\b", re.IGNORECASE)
_NEGATION = re.compile(r"\b(?:kein(?:e|en|er|em)?|nicht|verneint|verneinte|ohne)\b", re.IGNORECASE)
_UNCERTAINTY = re.compile(r"\b(?:möglicherweise|moeglicherweise|vielleicht|eventuell|vermutlich|scheint|wohl|unklar)\b", re.IGNORECASE)


def _span(source: SourceDocument, start: int, end: int) -> SourceSpan:
    return SourceSpan(sourceId=source.source_id, sourceVersion=source.source_version, start=start, end=end)


def _find_clauses(text: str) -> list[tuple[int, int, str]]:
    clauses: list[tuple[int, int, str]] = []
    cursor = 0
    for match in _CLAUSE_SPLIT.finditer(text):
        end = match.start()
        raw = text[cursor:end].strip()
        if raw:
            start = cursor + len(text[cursor:end]) - len(text[cursor:end].lstrip())
            clauses.append((start, start + len(raw), raw))
        cursor = match.end()
    raw = text[cursor:].strip()
    if raw:
        start = cursor + len(text[cursor:]) - len(text[cursor:].lstrip())
        clauses.append((start, start + len(raw), raw))
    return clauses


def _subject(clause: str) -> str | None:
    if re.search(r"\b(?:frau|herr|bewohner(?:in)?|patient(?:in)?)\b", clause, re.IGNORECASE):
        return "care_recipient"
    if re.search(r"\bich\b", clause, re.IGNORECASE):
        return "caregiver"
    return None


def _attribution(clause: str) -> Attribution:
    if re.search(r"\b(?:klagte|berichtet|gibt an|sagt|verneint)\b", clause, re.IGNORECASE):
        return Attribution.CARE_RECIPIENT
    if re.search(r"\b(?:beobachtet|wirkte|erscheint|zeigt)\b", clause, re.IGNORECASE):
        return Attribution.CAREGIVER
    return Attribution.UNSPECIFIED


def _laterality(clause: str) -> Laterality:
    left = bool(_LEFT.search(clause))
    right = bool(_RIGHT.search(clause))
    if left and right:
        return Laterality.BILATERAL
    if left:
        return Laterality.LEFT
    if right:
        return Laterality.RIGHT
    if re.search(r"\b(?:beidseitig|beide)\b", clause, re.IGNORECASE):
        return Laterality.BILATERAL
    return Laterality.NONE


def _make_fact(source: SourceDocument, run_id: str, start: int, end: int, clause: str, category: SourceFactCategory, *, numeric: str | None = None, unit: str | None = None, approximation: Approximation = Approximation.UNKNOWN, care_action: str | None = None, mobility: str | None = None) -> SourceFact:
    certainty = Certainty.UNCERTAIN if _UNCERTAINTY.search(clause) else Certainty.CERTAIN
    expectation, policy_key = expectation_for(category, explicit_uncertainty=certainty is Certainty.UNCERTAIN)
    if category is SourceFactCategory.OBSERVATION and certainty is Certainty.UNCERTAIN:
        expectation, policy_key = expectation_for(SourceFactCategory.SYMPTOM, explicit_uncertainty=True)
    return SourceFact(
        sourceFactId=f"{run_id}:fact-{start}-{end}", sourceFactExtractionRunId=run_id,
        sourceId=source.source_id, sourceVersion=source.source_version, residentContext=_context(source),
        sourceTextHash=source_text_hash(source.transcript_text), normalizationPolicy=NORMALIZATION_POLICY,
        category=category, factText=clause, subject=_subject(clause),
        polarity=Polarity.NEGATED if _NEGATION.search(clause) else Polarity.AFFIRMED,
        certainty=certainty, attribution=_attribution(clause),
        temporalText=(_TIME.search(clause).group(0) if _TIME.search(clause) else None),
        laterality=_laterality(clause), numericValue=numeric, unit=unit, approximation=approximation,
        mobilityAssistance=mobility, careAction=care_action,
        documentationExpectation=expectation, severityPolicyKey=policy_key,
        sourceSpans=(_span(source, start, end),),
    )


class HeuristicGermanSourceFactExtractor:
    """Small deterministic extractor for the PoC's documented German fact families."""

    provider_version = "heuristic-v1"
    model_version = None
    prompt_version = None

    def extract(self, source: SourceDocument, *, extraction_run_id: str | None = None) -> SourceFactExtractionResult:
        run_id = extraction_run_id or f"source-fact-extraction-{uuid4()}"
        facts: list[SourceFact] = []
        unresolved: list[UnresolvedSourceItem] = []
        for start, end, clause in _find_clauses(source.transcript_text):
            lower = clause.casefold()
            measurements = list(_MEASUREMENT.finditer(clause))
            if measurements:
                for measurement in measurements:
                    raw_unit = measurement.group("unit").casefold().replace("°", "")
                    unit = "BEATS_PER_MINUTE" if raw_unit.startswith(("bpm", "schl")) else {
                        "c": "CELSIUS",
                        "celsius": "CELSIUS",
                        "grad": "CELSIUS",
                        "bpm": "BEATS_PER_MINUTE",
                        "schläge pro minute": "BEATS_PER_MINUTE",
                        "schlaege pro minute": "BEATS_PER_MINUTE",
                    }[raw_unit]
                    facts.append(_make_fact(source, run_id, start, end, clause, SourceFactCategory.MEASUREMENT,
                                            numeric=measurement.group("value").replace(",", "."), unit=unit,
                                            approximation=Approximation.APPROXIMATE if measurement.group("approximation") else Approximation.EXACT))
                continue
            measurement = None
            if not measurement:
                measurement = re.search(
                    r"(?:(?:trank|getrunken|aufnahme|menge|dosis|erhielt|verabreicht)\s*)"
                    r"(ca\.\s*)?(-?\d+(?:[,.]\d+)?)\s*(mmhg|ml|mg|g|l)\b",
                    clause,
                    re.IGNORECASE,
                )
            if measurement:
                raw_unit = measurement.group(3).casefold().replace("°", "")
                unit = {
                    "c": "CELSIUS",
                    "celsius": "CELSIUS",
                    "grad": "CELSIUS",
                    "ml": "MILLILITRE",
                    "l": "LITRE",
                    "mg": "MILLIGRAM",
                    "g": "GRAM",
                    "mmhg": "MMHG",
                }[raw_unit]
                facts.append(_make_fact(source, run_id, start, end, clause, SourceFactCategory.MEASUREMENT,
                                        numeric=measurement.group(2).replace(",", "."), unit=unit,
                                        approximation=Approximation.APPROXIMATE if measurement.group(1) else Approximation.EXACT))
                continue
            if "unklar" in lower and not any(word in lower for word in ("schmerz", "schwindel", "übel", "uebel", "müde", "muede")):
                unresolved.append(UnresolvedSourceItem(
                    unresolvedSourceItemId=f"{run_id}:unresolved-{start}", sourceFactExtractionRunId=run_id,
                    sourceId=source.source_id, sourceVersion=source.source_version, residentContext=_context(source),
                    sourceTextHash=source_text_hash(source.transcript_text), normalizationPolicy=NORMALIZATION_POLICY,
                    candidateSourceSpans=(_span(source, start, end),), explanation="The source clause is explicitly marked unclear.",
                ))
                continue
            if re.search(r"\b(?:schmerz|schmerzen|schwindel|übelkeit|uebelkeit|müde|muede|atemnot|husten)\w*\b", lower):
                facts.append(_make_fact(source, run_id, start, end, clause, SourceFactCategory.SYMPTOM))
            if re.search(r"\b(?:hilfe|unterstützung|unterstuetzung|rollator|transfer|gehen|laufen|aufstehen)\w*\b", lower):
                facts.append(_make_fact(source, run_id, start, end, clause, SourceFactCategory.MOBILITY, mobility=clause))
            if re.search(r"\b(?:gewaschen|geduscht|gelagert|verband gewechselt|medikament verabreicht|geholfen|versorgt)\b", lower):
                facts.append(_make_fact(source, run_id, start, end, clause, SourceFactCategory.CARE_ACTION, care_action=clause))
            if not facts or all(f.source_spans[0].start != start for f in facts):
                if re.search(r"\b(?:wirkte|beobachtet|ruhig|schlief|aß|ass|trank)\w*\b", lower):
                    facts.append(_make_fact(source, run_id, start, end, clause, SourceFactCategory.OBSERVATION))
        result = SourceFactExtractionResult(
            extraction_run_id=run_id, source_id=source.source_id, source_version=source.source_version,
            source_text_hash=source_text_hash(source.transcript_text), normalization_policy=NORMALIZATION_POLICY,
            facts=tuple(facts), unresolved_items=tuple(unresolved), provider_version=self.provider_version,
            model_version=self.model_version, prompt_version=self.prompt_version,
        )
        validate_extraction_result(result, source)
        return result
