"""Provider boundary and deterministic synthetic test adapter."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Protocol

from .contracts import CandidateNursingFact, GenerationResult, SourceAnchor
from .errors import NoteError, NoteErrorCode


class GenerationAdapter(Protocol):
    """The only interface the note service uses for model-backed generation."""

    def generate(self, source: Any) -> GenerationResult | Mapping[str, object]: ...


class UnavailableGenerationAdapter:
    """Default production boundary when no live provider is configured."""

    def generate(self, source: Any) -> GenerationResult:
        raise NoteError(
            NoteErrorCode.GENERATION_PROVIDER_UNAVAILABLE,
            "No nursing-note generation provider is configured.",
        )


class DeterministicNursingNoteAdapter:
    """Synthetic, offline adapter for CI; it is not a live-model implementation."""

    model_id = "deterministic-test-double"
    prompt_version = "test-fixture-v1"
    schema_version = "nursing-fact-v1"
    ruleset_version = "generation-guardrails-v1"

    def __init__(self) -> None:
        self.invocation_count = 0

    def generate(self, source: Any) -> GenerationResult:
        self.invocation_count += 1
        facts: list[CandidateNursingFact] = []
        sentence_pattern = re.compile(r"[^.!?\r\n]+(?:[.!?]|$)")
        for match in sentence_pattern.finditer(source.transcript_text):
            raw = match.group(0)
            leading = len(raw) - len(raw.lstrip())
            statement = raw.strip()
            if not statement:
                continue
            start = match.start() + leading
            end = start + len(statement)
            lower = statement.casefold()
            numeric_match = re.search(
                r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>°C|mmHg|kg|cm|ml|bpm|g|l|%)",
                statement,
                flags=re.IGNORECASE,
            )
            if numeric_match:
                fact_type = "MEASUREMENT"
            elif any(word in lower for word in ("schmerz", "übel", "schwindel", "husten", "müd", "schlaf")):
                fact_type = "SYMPTOM"
            elif any(word in lower for word in ("wurde", "erhielt", "angeboten", "gelagert", "durchgeführt", "gepflegt")):
                fact_type = "ACTION"
            else:
                fact_type = "OBSERVATION"

            if re.search(r"\b(kein|keine|keinen|nicht|verneint|ohne)\b", lower):
                polarity = "NEGATED"
            else:
                polarity = "AFFIRMED"
            certainty = "UNCERTAIN" if re.search(r"\b(möglicherweise|vermutlich|eventuell|scheint|könnte)\b", lower) else "CERTAIN"
            if re.search(r"\b(?:bewohner(?:in)?|resident(?:in)?|frau|herr)\b.*\b(?:berichtet|gibt an|sagt|klagt)\b", lower):
                attribution = "RESIDENT_REPORTED"
            elif "pflegekraft" in lower or "beobachtet" in lower:
                attribution = "CAREGIVER_OBSERVED"
            else:
                attribution = None
            facts.append(
                CandidateNursingFact(
                    type=fact_type,
                    statement=statement,
                    residentSubject=source.resident_test_id,
                    sourceAnchor=SourceAnchor(
                        sourceId=source.source_id,
                        sourceVersion=source.source_version,
                        start=start,
                        end=end,
                    ),
                    polarity=polarity,
                    certainty=certainty,
                    attribution=attribution,
                    numericValue=numeric_match.group("value") if numeric_match else None,
                    unit=numeric_match.group("unit") if numeric_match else None,
                    provenance="GENERATED_FROM_SOURCE",
                )
            )
        return GenerationResult(
            content=f"Pflegedokumentation:\n{source.transcript_text}",
            facts=tuple(facts),
            modelId=self.model_id,
            promptVersion=self.prompt_version,
            schemaVersion=self.schema_version,
            rulesetVersion=self.ruleset_version,
        )
