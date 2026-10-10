"""Bounded, deterministic generation-time fidelity checks."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .contracts import CandidateNursingFact, GenerationResult
from .errors import NoteError, NoteErrorCode


_UNSUPPORTED_DIAGNOSIS = re.compile(
    r"\b(?:diagnose|diagnostiziert|diagnoseverdacht|pneumonie|demenz|depression|diabetes|herzinsuffizienz)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(r"\b(?:kein|keine|keinen|nicht|verneint|ohne)\b", re.IGNORECASE)
_UNCERTAINTY = re.compile(r"\b(?:möglicherweise|vermutlich|eventuell|scheint|könnte)\b", re.IGNORECASE)
_RESIDENT_REPORT = re.compile(
    r"\b(?:bewohner(?:in)?|resident(?:in)?|frau|herr)\b.*\b(?:berichtet|gibt an|sagt|klagt)\b",
    re.IGNORECASE,
)
_CAREGIVER_OBSERVATION = re.compile(r"\b(?:pflegekraft|beobachtet)\b", re.IGNORECASE)
_TOKEN = re.compile(r"[\wÄÖÜäöüß]+", re.UNICODE)
_MEASUREMENT = re.compile(r"\d+(?:[.,]\d+)?\s*(?:°C|mmHg|kg|cm|ml|bpm|g|l|%)", re.IGNORECASE)


def _reject(message: str, field: str | None = None) -> None:
    raise NoteError(NoteErrorCode.GENERATION_REJECTED, message, field)


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value) if len(token) > 2}


class GenerationGuardrails:
    """Validate only contract and explicitly bounded source-fidelity properties."""

    schema_version = "nursing-fact-v1"
    ruleset_version = "generation-guardrails-v1"
    normalization_policy = "unicode-code-point-v1"

    def validate(self, result: GenerationResult, source: Any) -> None:
        if not result.facts:
            raise NoteError(NoteErrorCode.EMPTY_MODEL_OUTPUT, "The generation provider returned no nursing facts.")

        if "de" not in source.language.casefold():
            _reject("Generation requires a German source document.", "sourceVersion")

        for index, fact in enumerate(result.facts):
            self._validate_fact(fact, source, index)
        self._reject_new_clinical_conclusions(result, source)

    def _validate_fact(self, fact: CandidateNursingFact, source: Any, index: int) -> None:
        anchor = fact.source_anchor
        if fact.provenance != "GENERATED_FROM_SOURCE":
            _reject("Generated facts must be marked as generated from the source.", f"facts.{index}.provenance")
        if fact.resident_subject not in {source.resident_test_id, "UNKNOWN"}:
            _reject("A generated fact names an unsupported resident subject.", f"facts.{index}.residentSubject")
        if (
            anchor.source_id != source.source_id
            or anchor.source_version != source.source_version
            or anchor.start is None
            or anchor.end is None
        ):
            _reject("A generated fact references a different or incomplete source anchor.", f"facts.{index}.sourceAnchor")
        if not 0 <= anchor.start < anchor.end <= len(source.transcript_text):
            _reject("A generated fact has an out-of-range source anchor.", f"facts.{index}.sourceAnchor")

        excerpt = source.transcript_text[anchor.start : anchor.end]
        if not _tokens(fact.statement).intersection(_tokens(excerpt)):
            _reject("A generated fact is not anchored to its stated source text.", f"facts.{index}.statement")

        lower = excerpt.casefold()
        has_negation = _NEGATION.search(excerpt) is not None
        if has_negation and fact.polarity != "NEGATED":
            _reject("Explicit source negation was not preserved.", f"facts.{index}.polarity")
        if not has_negation and fact.polarity == "NEGATED":
            _reject("A negated fact is not supported by its source anchor.", f"facts.{index}.polarity")

        has_uncertainty = _UNCERTAINTY.search(excerpt) is not None
        if has_uncertainty and fact.certainty != "UNCERTAIN":
            _reject("Explicit source uncertainty was not preserved.", f"facts.{index}.certainty")
        if not has_uncertainty and fact.certainty == "UNCERTAIN":
            _reject("An uncertain fact is not supported by its source anchor.", f"facts.{index}.certainty")

        if _RESIDENT_REPORT.search(excerpt):
            if fact.attribution != "RESIDENT_REPORTED":
                _reject("Resident-reported information must retain its attribution.", f"facts.{index}.attribution")
        elif fact.attribution == "RESIDENT_REPORTED":
            _reject("Resident attribution is not supported by the source anchor.", f"facts.{index}.attribution")

        if _CAREGIVER_OBSERVATION.search(excerpt) and fact.attribution not in {None, "CAREGIVER_OBSERVED"}:
            _reject("Caregiver observation attribution was changed.", f"facts.{index}.attribution")

        source_measurement = _MEASUREMENT.search(excerpt)
        if source_measurement:
            if fact.numeric_value is None or fact.unit is None:
                _reject("A source measurement must retain its value and unit.", f"facts.{index}")
            if fact.numeric_value not in source_measurement.group(0) or fact.unit not in source_measurement.group(0):
                _reject("A generated measurement changed its source value or unit.", f"facts.{index}")
        elif fact.numeric_value is not None or fact.unit is not None:
            _reject("A numeric value or unit is not present in the source anchor.", f"facts.{index}")

    def _reject_new_clinical_conclusions(self, result: GenerationResult, source: Any) -> None:
        source_text = source.transcript_text.casefold()
        candidates: Iterable[str] = (result.content, *(fact.statement for fact in result.facts))
        for candidate in candidates:
            match = _UNSUPPORTED_DIAGNOSIS.search(candidate)
            if match and match.group(0).casefold() not in source_text:
                _reject("The generated output adds an unsupported diagnosis or clinical conclusion.", "content")
