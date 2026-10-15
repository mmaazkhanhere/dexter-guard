"""Composition adapters for the synchronous synthetic reliability workflow.

The domain packages deliberately expose small, transport-independent services. This
module is the application-level bridge that resolves one immutable note revision,
executes each upstream component, and returns only terminal run metadata to the
human-review orchestrator.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from claim_extraction.models import ExtractionStatus
from claim_extraction.repository import InMemoryClaimRepository
from claim_extraction.revision_reader import NursingNoteRevisionReader
from claim_extraction.service import ClaimExtractionService
from claim_extraction.spans import make_text_span
from deterministic_validation.contracts import (
    Alignment,
    Claim as DeterministicClaim,
    EvidenceReference,
    MeasurementCategory,
    SourceFact as DeterministicSourceFact,
    TranscriptSnapshot,
    Unit,
    ValidationRequest,
)
from deterministic_validation.repository import (
    InMemoryAlignmentRepository,
    InMemoryClaimRepository as InMemoryDeterministicClaimRepository,
    InMemorySourceFactRepository,
    InMemoryTranscriptRepository,
    InMemoryValidationRunRepository,
)
from deterministic_validation.service import DeterministicValidationService
from evidence_verification.contracts import VerificationRunRequest
from evidence_verification.repository import InMemoryVerificationRepository
from evidence_verification.service import VerificationService
from human_review.contracts import EvidenceDisplay, NoteSpan, ReviewFinding, SEVERITY_POLICY_VERSION
from human_review.ports import ReferenceOnlyVerificationPorts, UpstreamRun
from human_review.policy import severity_for
from resident_attribution import ResidentAttributionChecker
from app.observability import workflow_log, workflow_step
from nursing_notes.repository import NoteRepository
from source_coverage.contracts import CoverageRunRequest
from source_coverage.extraction import SourceFactExtractionResult, source_text_hash
from source_coverage.repository import (
    ClaimSetRecord,
    InMemoryClaimSetRepository,
    InMemoryCoverageRunRepository,
    InMemorySourceFactExtractionRepository,
)
from source_coverage.service import SourceCoverageService


class HeuristicClaimProvider:
    """Deterministic provider for the synthetic PoC claim boundary.

    The service still validates the complete claim contract and persists an immutable
    extraction result. A configured model provider can replace this adapter later
    without changing the orchestration ports.
    """

    provider_version = "heuristic-claim-provider-v2"
    model_version = None
    prompt_version = "claim-extraction-heuristic-v1"

    _sentences = re.compile(r"[^.!?\r\n]+(?:[.!?]|$)")
    _number = re.compile(
        r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>\u00b0?C|grad\s+celsius|celsius|grad|mmHg|ml|mg|bpm|schl(?:\u00e4|ae)ge[n]?\s+pro\s+minute|l\b|g\b)",
        re.IGNORECASE,
    )
    _coordinator = re.compile(r"(?:,\s*|\s+)(?P<word>und|sowie|aber)\s+", re.IGNORECASE)
    _predicate = re.compile(r"\b(?:ist|sind|war|waren|hat|haben|zeigt|zeigen|berichtet|klagt|wurde|wurden|erhielt|verabreicht|beträgt|liegt)\b", re.IGNORECASE)
    _atomic_continuation = re.compile(r"\b(?:wach|orientiert|ruhig|unruhig|schmerz|schwindel|übelkeit|uebelkeit|atemnot|husten|gewaschen|gelagert|unterstützt|unterstuetzt)\w*\b", re.IGNORECASE)

    def extract(
        self,
        note_text: str,
        *,
        note_revision_id: str | None = None,
        resident_test_id: str | None = None,
        **_: object,
    ) -> Mapping[str, object]:
        revision_id = note_revision_id or "note:unknown:r1"
        resident_id = resident_test_id or "synthetic-resident-unknown"
        claims: list[dict[str, object]] = []
        for match in self._sentences.finditer(note_text):
            raw = match.group(0)
            leading = len(raw) - len(raw.lstrip())
            statement = raw.strip()
            if not statement or statement.casefold().startswith("pflegedokumentation:") and len(statement.split()) == 1:
                continue
            start = match.start() + leading
            end = start + len(statement)
            if statement.casefold().startswith("pflegedokumentation:"):
                prefix = "Pflegedokumentation:"
                start += len(prefix)
                statement = note_text[start:end].lstrip()
                start = end - len(statement)
            segments = self._atomic_segments(statement, start)
            for segment_start, segment_end, segment in segments:
                claims.append(self._claim(
                    note_text, segment_start, segment_end, segment, revision_id, resident_id, len(claims) + 1,
                ))
        return {"claims": claims}

    @classmethod
    def _atomic_segments(cls, statement: str, start: int) -> list[tuple[int, int, str]]:
        """Split only coordinated, independently checkable assertions.

        Multiple measured values are always separate claims. A limited set of
        coordinated observation/action continuations is also split. Contrastive
        symptom or measurement clauses are split when each side is independently
        checkable, preserving each clause's local negation scope.
        """
        separators = list(cls._coordinator.finditer(statement))
        if not separators:
            return [(start, start + len(statement), statement)]
        raw_parts: list[tuple[int, int, str]] = []
        cursor = 0
        for separator in separators:
            raw_parts.append((cursor, separator.start(), statement[cursor:separator.start()]))
            cursor = separator.end()
        raw_parts.append((cursor, len(statement), statement[cursor:]))
        parts = []
        for raw_start, raw_end, raw in raw_parts:
            leading = len(raw) - len(raw.lstrip())
            text = raw.strip()
            if text:
                absolute_start = start + raw_start + leading
                parts.append((absolute_start, absolute_start + len(text), text))
        if len(parts) < 2:
            return [(start, start + len(statement), statement)]
        measurement_count = len(list(cls._number.finditer(statement)))
        coordinated_assertions = bool(cls._predicate.search(parts[0][2])) and all(
            cls._predicate.search(part[2]) or cls._atomic_continuation.search(part[2])
            for part in parts[1:]
        )
        contrastive_assertions = any(separator.group("word").casefold() == "aber" for separator in separators) and all(
            cls._number.search(part[2]) or cls._atomic_continuation.search(part[2])
            for part in parts
        )
        return parts if measurement_count >= 2 or coordinated_assertions or contrastive_assertions else [(start, start + len(statement), statement)]

    @classmethod
    def _claim(cls, note_text: str, start: int, end: int, statement: str, revision_id: str, resident_id: str, ordinal: int) -> dict[str, object]:
            statement_span = make_text_span(note_text, start, end)
            lower = statement.casefold()
            polarity = "NEGATED" if re.search(r"\b(?:kein|keine|keinen|nicht|verneint|ohne)\b", lower) else "AFFIRMED"
            certainty_match = re.search(r"\b(?:möglicherweise|moeglicherweise|vielleicht|eventuell|vermutlich|scheint)\w*\b", lower)
            certainty = "UNCERTAIN" if certainty_match else "CERTAIN"
            attribution = "UNSPECIFIED"
            category = "OBSERVATION"
            if re.search(r"\b(?:schmerz|schmerzen|schwindel|übelkeit|uebelkeit|müde|muede|atemnot|husten)\w*\b", lower):
                category = "SYMPTOM"
            number = cls._number.search(statement)
            numeric_values: list[dict[str, object]] = []
            if number:
                category = "NUTRITION_HYDRATION" if number.group("unit").casefold() in {"ml", "l"} else "MEASUREMENT"
                value_start = start + number.start("value")
                value_end = start + number.end("value")
                unit_start = start + number.start("unit")
                unit_end = start + number.end("unit")
                unit_raw = number.group("unit")
                unit_normalized = "BEATS_PER_MINUTE" if unit_raw.casefold().startswith(("bpm", "schl")) else {
                    "ml": "MILLILITRE", "l": "LITRE", "mg": "MILLIGRAM", "g": "GRAM",
                    "mmhg": "MMHG", "c": "CELSIUS", "°c": "CELSIUS", "grad": "CELSIUS",
                    "grad celsius": "CELSIUS", "celsius": "CELSIUS",
                    "bpm": "BEATS_PER_MINUTE", "schläge pro minute": "BEATS_PER_MINUTE",
                    "schlaege pro minute": "BEATS_PER_MINUTE",
                }[unit_raw.casefold()]
                numeric_values.append({
                    "raw": number.group("value"),
                    "normalizedDecimal": number.group("value").replace(",", "."),
                    "unitRaw": unit_raw,
                    "unitNormalized": unit_normalized,
                    "approximation": bool(re.search(r"\b(?:etwa|ca\.?|ungefähr|ungefaehr)\b", lower)),
                    "valueSpan": make_text_span(note_text, value_start, value_end).model_dump(by_alias=True),
                    "unitSpan": make_text_span(note_text, unit_start, unit_end).model_dump(by_alias=True),
                })
            claim: dict[str, object] = {
                "id": f"{revision_id}:c{ordinal}",
                "noteRevisionId": revision_id,
                "residentTestId": resident_id,
                "ordinal": ordinal,
                "category": category,
                "statementSpan": statement_span.model_dump(by_alias=True),
                "claimText": statement,
                "polarity": polarity,
                "certainty": certainty,
                "attribution": attribution,
                "numericValues": numeric_values,
                "extractionWarnings": [],
            }
            if polarity == "NEGATED":
                cue = re.search(r"\b(?:kein|keine|keinen|nicht|verneint|ohne)\b", statement, re.IGNORECASE)
                if cue:
                    claim["negationCue"] = make_text_span(note_text, start + cue.start(), start + cue.end()).model_dump(by_alias=True)
            if certainty_match:
                cue = re.search(certainty_match.group(0), statement, re.IGNORECASE)
                if cue:
                    claim["certaintyCue"] = make_text_span(note_text, start + cue.start(), start + cue.end()).model_dump(by_alias=True)
            return claim


class OfflineSemanticEvidenceProvider:
    """Conservative local fallback when the configured LLM verifier is unavailable.

    Production selects the configured OpenAI-compatible semantic verifier first.
    This offline adapter exists only to keep synthetic/local workflows runnable;
    it compares normalized German meaning cues rather than requiring literal
    sentence equality. Exact numeric and unit validation remains owned by the
    deterministic-validation component.
    """

    model_id = "offline-semantic-evidence-verifier"
    model_version = "offline-semantic-v1"
    prompt_version = "evidence-verification-offline-semantic-v1"
    prompt_hash = "sha256:evidence-verification-offline-semantic-v1"

    _sentences = re.compile(r"[^.!?\r\n]+(?:[.!?]|$)")
    _scopes = re.compile(r"(?:\s+(?:und|aber|doch|sowie)\s+|,\s+(?=[A-Za-zÄÖÜäöüß]))")
    _words = re.compile(r"[\wäöüÄÖÜß]+")
    _numbers = re.compile(r"-?\d+(?:[,.]\d+)?")
    _stop_words = frozenset({"die", "der", "das", "den", "dem", "des", "ein", "eine", "einer", "einem", "und", "oder", "aber", "doch", "sowie", "ist", "sind", "hat", "haben", "wurde", "wird", "bei", "im", "in", "am", "an", "zu", "von", "mit", "für", "über", "unter", "auf", "aus", "die", "frau", "herr", "bewohnerin", "bewohner", "patient", "patientin"})
    _semantic_terms = {
        "schmerz": "pain", "schmerzen": "pain", "beschwerde": "pain", "beschwerden": "pain",
        "verneint": "negated", "kein": "negated", "keine": "negated", "keinen": "negated", "ohne": "negated", "nicht": "negated",
        "möglich": "uncertain", "möglicherweise": "uncertain", "vielleicht": "uncertain", "unklar": "uncertain",
        "berichtet": "reported", "gibt": "reported", "an": "reported", "sagt": "reported", "klagt": "reported",
        "wirkt": "observed", "beobachtet": "observed", "erscheint": "observed",
        "fieber": "fever", "temperatur": "temperature", "trinkt": "drinks", "trank": "drinks", "wasser": "drinks",
        "schläft": "sleep", "geschlafen": "sleep", "schlief": "sleep", "ruhig": "calm", "entspannt": "calm",
        "schwindel": "dizziness", "übelkeit": "nausea", "uebelkeit": "nausea",
        "übel": "nausea", "uebel": "nausea", "husten": "cough", "rötung": "redness", "roetung": "redness",
        "unruhig": "restless", "blutdruck": "blood_pressure", "gewicht": "weight", "waage": "weight",
        "trinkmenge": "intake", "getrunken": "intake", "urinmenge": "urine", "urin": "urine",
        "strecke": "distance", "meter": "distance", "besuch": "visit", "besuchte": "visit",
        "besucht": "visit", "nahm": "intake", "aß": "intake",
    }

    _attribution_markers = re.compile(r"\b(?:bericht(?:et|ete)?|sagt(?:e)?|beobachtet(?:e)?|bat|bot)\b", re.IGNORECASE)

    @staticmethod
    def _attribution_role(text: str) -> str | None:
        lowered = text.casefold()
        if re.search(r"\b(?:sohn|tochter|angehörige|angehoerige)\b", lowered):
            return "relative"
        if re.search(r"\b(?:pflegekraft|pflege)\b", lowered):
            return "caregiver"
        if re.search(r"\b(?:bewohnerin|bewohner|patientin|patient)\b", lowered):
            return "resident"
        return None

    @classmethod
    def _numeric_values(cls, text: str) -> tuple[str, ...]:
        return tuple(value.replace(",", ".") for value in cls._numbers.findall(text))

    def verify(self, *, claims, source_text: str, run_id: str, source_id: str | None = None, source_version: int | None = None):
        findings = []
        for candidate in claims:
            claim_text = str(getattr(candidate, "claim_text", "")).strip()
            status, explanation, start, end, discrepancies = self._classify(claim_text, source_text)
            spans = []
            if start is not None and source_id is not None and source_version is not None:
                spans = [{"sourceId": source_id, "sourceVersion": source_version, "start": start, "end": end}]
            findings.append({"claimId": candidate.id, "status": status, "explanation": explanation, "sourceSpans": spans, "discrepancies": discrepancies})
        return {"findings": findings}

    @classmethod
    def _meaning_tokens(cls, text: str) -> set[str]:
        tokens: set[str] = set()
        for word in cls._words.findall(text.casefold()):
            if word in cls._stop_words:
                continue
            token = cls._semantic_terms.get(word, word)
            if len(token) > 4 and token.endswith(("en", "er", "es", "em", "e")):
                token = token.rstrip("enrsm")
            tokens.add(token)
        return tokens

    @classmethod
    def _classify(cls, claim_text: str, source_text: str) -> tuple[str, str, int | None, int | None, list[str]]:
        claim_tokens = cls._meaning_tokens(claim_text)
        best: tuple[set[str], int, int, str] | None = None
        best_score: tuple[int, int, int] = (-1, -1, -1)
        for match in cls._sentences.finditer(source_text):
            sentence = match.group(0)
            scope_start = 0
            boundaries = list(cls._scopes.finditer(sentence))
            for boundary in boundaries + [None]:
                scope_end = boundary.start() if boundary is not None else len(sentence)
                raw_scope = sentence[scope_start:scope_end]
                scope = raw_scope.strip()
                leading_trim = len(raw_scope) - len(raw_scope.lstrip())
                absolute_start = match.start() + scope_start + leading_trim
                absolute_end = absolute_start + len(scope)
                scope_tokens = cls._meaning_tokens(scope)
                overlap = claim_tokens & scope_tokens
                semantic_overlap = len(overlap & set(cls._semantic_terms.values()))
                numeric_match = int(bool(cls._numeric_values(claim_text)) and bool(cls._numeric_values(scope)))
                score = (semantic_overlap, numeric_match, len(overlap))
                if best is None or score > best_score:
                    best = (overlap, absolute_start, absolute_end, scope)
                    best_score = score
                if boundary is None:
                    break
                scope_start = boundary.end()
        if best is None or not best[0]:
            return "UNSUPPORTED", "No source statement establishes the claim's meaning.", None, None, []

        overlap, start, end, sentence = best
        source_tokens = cls._meaning_tokens(sentence)
        semantic_cues = set(cls._semantic_terms.values())
        if not (overlap & semantic_cues) and len(overlap) < 2:
            return "UNSUPPORTED", "The source shares only an identity reference, not clinical evidence for the claim.", None, None, []
        claim_negated = "negated" in claim_tokens
        source_negated = "negated" in source_tokens
        if claim_negated != source_negated and overlap - {"negated"}:
            return "CONTRADICTED", "The source expresses the opposite polarity for the same subject matter.", start, end, ["NEGATION"]
        claim_numbers = cls._numeric_values(claim_text)
        source_numbers = cls._numeric_values(sentence)
        if claim_numbers and source_numbers and claim_numbers != source_numbers and overlap:
            return "CONTRADICTED", "The source gives a different numeric value for the same subject matter.", start, end, ["OTHER"]
        claim_role = cls._attribution_role(claim_text)
        source_role = cls._attribution_role(sentence)
        if (
            claim_role is not None and source_role is not None and claim_role != source_role
            and (cls._attribution_markers.search(claim_text) or cls._attribution_markers.search(sentence))
            and overlap
        ):
            return "CONTRADICTED", "The source attributes the statement to a different person.", start, end, ["ATTRIBUTION"]
        if "uncertain" in source_tokens and "uncertain" not in claim_tokens:
            return "UNCERTAIN", "The source qualifies this information, so the unqualified claim is not established.", start, end, ["CERTAINTY"]
        material_cues = {"reported", "observed", "uncertain", "negated"}
        semantic_values = set(cls._semantic_terms.values())
        material_claim_tokens = (claim_tokens - material_cues) & semantic_values
        material_source_tokens = (source_tokens - material_cues) & semantic_values
        if material_claim_tokens and material_claim_tokens <= material_source_tokens:
            return "SUPPORTED", "The source supports the claim's meaning, including its material qualifiers.", start, end, []
        if len(overlap) >= 2:
            return "SUPPORTED", "The source supports the same material facts using a paraphrase.", start, end, []
        if overlap:
            return "UNCERTAIN", "The source is related but does not establish every material part of the claim.", start, end, ["OTHER"]
        return "UNSUPPORTED", "No source statement establishes the claim's meaning.", None, None, []


class WorkflowVerificationPorts:
    """Run the four upstream services in the order required by human review."""

    def __init__(self, *, source_service, note_repository: NoteRepository, review_service, claim_service: ClaimExtractionService, evidence_service: VerificationService, coverage_service: SourceCoverageService, validation_service: DeterministicValidationService, validation_transcripts: InMemoryTranscriptRepository, validation_facts: InMemorySourceFactRepository, validation_claims: InMemoryDeterministicClaimRepository, validation_alignments: InMemoryAlignmentRepository, validation_runs: InMemoryValidationRunRepository, extraction_repository: InMemorySourceFactExtractionRepository, claim_sets: InMemoryClaimSetRepository):
        self.source_service = source_service
        self.note_repository = note_repository
        self.review_service = review_service
        self.validation_service = validation_service
        self.validation_transcripts = validation_transcripts
        self.validation_facts = validation_facts
        self.validation_claims = validation_claims
        self.validation_alignments = validation_alignments
        self.claim_service = claim_service
        self.evidence_service = evidence_service
        self.coverage_service = coverage_service
        self.validation_runs = validation_runs
        self.extraction_repository = extraction_repository
        self.claim_sets = claim_sets

    def _note(self, note_id: str, revision: int):
        return self.note_repository.get(note_id, revision)

    def _source(self, note_id: str, revision: int):
        note = self._note(note_id, revision)
        return note, self.source_service.get_source_version(note.source_id, note.source_version)

    def extract(self, note_id: str, revision: int) -> UpstreamRun:
        with workflow_step("CLAIM_EXTRACTION", "CLAIM_EXTRACTION", noteId=note_id, noteRevision=revision):
            note, source = self._source(note_id, revision)
            result = self.claim_service.extract_claims(f"{note_id}:r{revision}")
        claim_set_id = result.extraction_run_id
        if result.status in {ExtractionStatus.SUCCEEDED, ExtractionStatus.EMPTY}:
            source_facts = self.coverage_service.extractor.extract(source, extraction_run_id=f"source-facts-{claim_set_id}")
            self.extraction_repository._items[source_facts.extraction_run_id] = source_facts
            self.claim_sets._items[claim_set_id] = ClaimSetRecord(
                claim_set_id=claim_set_id, note_id=note_id, note_revision=revision,
                resident_test_id=source.resident_test_id, source_id=source.source_id,
                source_version=source.source_version, claims=tuple(result.claims),
            )
            self._persist_resident_attribution_findings(claim_set_id, note_id, revision, result.claims, source)
        run = UpstreamRun(
            run_id=result.extraction_run_id,
            status="SUCCEEDED" if result.status in {ExtractionStatus.SUCCEEDED, ExtractionStatus.EMPTY} else "FAILED",
            source_id=source.source_id, source_version=source.source_version,
            note_id=note_id, note_revision=revision, claim_set_id=claim_set_id,
        )
        workflow_log("CLAIM_EXTRACTION", "CLAIM_EXTRACTION_RESULT", outcome="SUCCESS" if run.status == "SUCCEEDED" else "ERROR", noteId=note_id, noteRevision=revision, runId=run.run_id, status=run.status, claimCount=len(result.claims))
        return run

    def _persist_resident_attribution_findings(self, claim_set_id, note_id, revision, claims, source) -> None:
        for finding in ResidentAttributionChecker().check(source=source, claims=claims):
            finding_id = f"review-resident-{claim_set_id}-{finding.claim_id}-{finding.rule_code}"
            if finding_id in self.review_service.repository.findings:
                continue
            claim = next((item for item in claims if item.id == finding.claim_id), None)
            severity, rationale = severity_for(
                origin="SPEC_005", rule_code=finding.rule_code,
                claim_text=claim.claim_text if claim else None,
                resident_misassignment=finding.outcome == "MISMATCH",
            )
            self.review_service.add_finding(ReviewFinding(
                reviewFindingId=finding_id, origin="SPEC_005", originRunId=f"resident-attribution-{claim_set_id}",
                originFindingId=f"{finding.claim_id}:{finding.rule_code}", noteId=note_id, noteRevision=revision,
                sourceId=source.source_id, sourceVersion=source.source_version, claimId=finding.claim_id,
                claimSpan=self._claim_span(claims, finding.claim_id), upstreamStatus=finding.outcome,
                ruleCode=finding.rule_code, severity=severity, severityPolicyVersion=SEVERITY_POLICY_VERSION,
                severityRationale=rationale, explanation=finding.explanation,
                evidence=self._source_evidence(source, tuple(type("Span", (), {"source_id": source.source_id, "source_version": source.source_version, "start": start, "end": end})() for start, end in finding.evidence)),
                state="OPEN", createdAt=datetime.now(timezone.utc),
            ))

    def evidence(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        workflow_log("EVIDENCE_VERIFICATION", "EVIDENCE_VERIFICATION_STARTED", noteId=note_id, noteRevision=revision, claimSetId=claim_set_id)
        note, source = self._source(note_id, revision)
        result = self.claim_service.repository.get_current_result(f"{note_id}:r{revision}")
        if result is None or result.extraction_run_id != claim_set_id or not result.claims:
            raise LookupError("CLAIM_SET_NOT_FOUND")
        request = VerificationRunRequest(
            sourceId=source.source_id, sourceVersion=source.source_version,
            noteId=note_id, noteRevision=revision, claimSetId=claim_set_id,
            idempotencyKey=f"evidence:{note_id}:{revision}:{claim_set_id}",
            claims=tuple({"claimId": claim.id, "residentTestId": claim.resident_test_id} for claim in result.claims),
        )
        run = self.evidence_service.verify(request)
        self._persist_evidence_findings(run, result.claims, source)
        status = "SUCCEEDED" if getattr(run, "status", None) == "SUCCEEDED" else "FAILED"
        upstream = UpstreamRun(run_id=run.verification_run_id, status=status, source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)
        workflow_log("EVIDENCE_VERIFICATION", "EVIDENCE_VERIFICATION_RESULT", outcome="SUCCESS" if status == "SUCCEEDED" else "ERROR", noteId=note_id, noteRevision=revision, runId=upstream.run_id, status=status, findingCount=len(getattr(run, "findings", ())))
        return upstream

    def _claim_span(self, claims, claim_id: str | None) -> NoteSpan | None:
        if not claim_id:
            return None
        original_claim_id = claim_id.removeprefix("dve-")
        claim = next((item for item in claims if item.id == claim_id or item.id == original_claim_id), None)
        if claim is None:
            return None
        return NoteSpan(
            startCodePoint=claim.statement_span.start_code_point,
            endCodePointExclusive=claim.statement_span.end_code_point_exclusive,
            text=claim.statement_span.text,
        )

    @staticmethod
    def _source_evidence(source, spans, excerpts=()) -> EvidenceDisplay:
        source_spans = tuple(
            {
                "sourceId": item.source_id,
                "sourceVersion": item.source_version,
                "start": item.start,
                "end": item.end,
            }
            for item in spans
        )
        if not source_spans:
            return EvidenceDisplay(availability="MISSING")
        quoted = tuple(excerpts) or tuple(source.transcript_text[item["start"]:item["end"]] for item in source_spans)
        return EvidenceDisplay(availability="AVAILABLE", spans=source_spans, excerpts=quoted)

    def _persist_evidence_findings(self, run, claims, source) -> None:
        if getattr(run, "status", None) != "SUCCEEDED":
            return
        claims_by_id = {claim.id: claim for claim in claims}
        for finding in getattr(run, "findings", ()):
            if finding.status.value == "SUPPORTED":
                continue
            finding_id = f"review-{run.verification_run_id}-{finding.claim_id}"
            if finding_id in self.review_service.repository.findings:
                continue
            claim = claims_by_id.get(finding.claim_id)
            claim_span = self._claim_span(claims, finding.claim_id)
            if finding.source_spans:
                spans = tuple({
                    "sourceId": item.source_id,
                    "sourceVersion": item.source_version,
                    "start": item.start,
                    "end": item.end,
                } for item in finding.source_spans)
                evidence = EvidenceDisplay(
                    availability="AVAILABLE",
                    spans=spans,
                    excerpts=tuple(source.transcript_text[item.start:item.end] for item in finding.source_spans),
                )
            else:
                evidence = EvidenceDisplay(availability="MISSING")
            severity, rationale = severity_for(
                origin="SPEC_004",
                status=finding.status.value,
                claim_text=claim.claim_text if claim is not None else None,
                discrepancy_codes=(item.value for item in finding.discrepancies),
            )
            self.review_service.add_finding(ReviewFinding(
                reviewFindingId=finding_id,
                origin="SPEC_004",
                originRunId=run.verification_run_id,
                originFindingId=finding.claim_id,
                noteId=run.note_id,
                noteRevision=run.note_revision,
                sourceId=run.source_id,
                sourceVersion=run.source_version,
                claimId=finding.claim_id,
                claimSpan=claim_span,
                upstreamStatus=finding.status.value,
                severity=severity,
                severityPolicyVersion=SEVERITY_POLICY_VERSION,
                severityRationale=rationale,
                explanation=finding.explanation,
                evidence=evidence,
                state="OPEN",
                createdAt=datetime.now(timezone.utc),
            ))

    def _persist_validation_findings(self, run, claims, source) -> None:
        for index, finding in enumerate(getattr(run, "findings", ()), start=1):
            origin_finding_id = f"{run.validation_run_id}:{finding.rule_id}:{finding.source_fact_id or finding.claim_id or index}"
            review_finding_id = f"review-{origin_finding_id}"
            if review_finding_id in self.review_service.repository.findings:
                continue
            source_spans = ()
            if finding.source_fact_id:
                try:
                    source_fact = self.validation_facts.get(finding.source_fact_id)
                    source_spans = tuple(source_fact.evidence)
                except KeyError:
                    source_spans = ()
            claim_id = finding.claim_id.removeprefix("dve-") if finding.claim_id else None
            claim = next((item for item in claims if item.id == claim_id), None)
            severity, rationale = severity_for(
                origin="SPEC_005",
                rule_code=finding.rule_id,
                claim_text=claim.claim_text if claim is not None else None,
            )
            explanation = finding.message
            if finding.expected_value is not None or finding.observed_value is not None:
                explanation = f"{explanation} Expected: {finding.expected_value}; observed: {finding.observed_value}."
            self.review_service.add_finding(ReviewFinding(
                reviewFindingId=review_finding_id,
                origin="SPEC_005",
                originRunId=run.validation_run_id,
                originFindingId=origin_finding_id,
                noteId=run.note_id,
                noteRevision=run.note_revision,
                sourceId=run.source_id,
                sourceVersion=run.source_version,
                claimId=claim_id,
                claimSpan=self._claim_span(claims, finding.claim_id),
                upstreamStatus=getattr(finding.outcome, "value", finding.outcome),
                ruleCode=finding.rule_id,
                severity=severity,
                severityPolicyVersion=SEVERITY_POLICY_VERSION,
                severityRationale=rationale,
                explanation=explanation,
                evidence=self._source_evidence(source, source_spans),
                state="OPEN",
                createdAt=datetime.now(timezone.utc),
            ))

    def _persist_coverage_findings(self, run, claims, source) -> None:
        for finding in getattr(run, "findings", ()):
            review_finding_id = f"review-{run.coverage_run_id}-{finding.coverage_finding_id}"
            if review_finding_id in self.review_service.repository.findings:
                continue
            severity, rationale = severity_for(
                origin="SPEC_006",
                status=getattr(finding.status, "value", finding.status),
                policy_key=finding.severity_policy_key,
            )
            self.review_service.add_finding(ReviewFinding(
                reviewFindingId=review_finding_id,
                origin="SPEC_006",
                originRunId=run.coverage_run_id,
                originFindingId=finding.coverage_finding_id,
                noteId=run.note_id,
                noteRevision=run.note_revision,
                sourceId=run.source_id,
                sourceVersion=run.source_version,
                claimId=finding.matched_claim_ids[0] if finding.matched_claim_ids else None,
                claimSpan=self._claim_span(claims, finding.matched_claim_ids[0] if finding.matched_claim_ids else None),
                upstreamStatus=getattr(finding.status, "value", finding.status),
                ruleCode=f"COVERAGE-{getattr(finding.status, 'value', finding.status)}",
                severity=severity,
                severityPolicyVersion=SEVERITY_POLICY_VERSION,
                severityRationale=rationale,
                explanation=f"{getattr(finding.status, 'value', finding.status)}: {finding.suggestion}",
                evidence=self._source_evidence(source, finding.source_spans, finding.source_quotes),
                state="OPEN",
                createdAt=datetime.now(timezone.utc),
            ))

    def validation(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        workflow_log("DETERMINISTIC_VALIDATION", "DETERMINISTIC_VALIDATION_STARTED", noteId=note_id, noteRevision=revision, claimSetId=claim_set_id)
        note, source = self._source(note_id, revision)
        result = self.claim_service.repository.get_current_result(f"{note_id}:r{revision}")
        extraction = self.extraction_repository.get(f"source-facts-{claim_set_id}")
        if result is None or result.extraction_run_id != claim_set_id:
            raise LookupError("CLAIM_SET_NOT_FOUND")
        uncomparable_numeric = self._persist_uncomparable_numeric_findings(
            note_id, revision, claim_set_id, extraction, result.claims, source,
        )
        prepared = _deterministic_records(source, note_id, revision, extraction, result.claims)
        if prepared is None:
            upstream = UpstreamRun(run_id=f"validation-{claim_set_id}", status="FAILED" if uncomparable_numeric else "SUCCEEDED", source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)
            workflow_log("DETERMINISTIC_VALIDATION", "DETERMINISTIC_VALIDATION_RESULT", outcome="SUCCESS" if upstream.status == "SUCCEEDED" else "ERROR", noteId=note_id, noteRevision=revision, runId=upstream.run_id, status=upstream.status, findingCount=0)
            return upstream
        snapshot, facts, claims, alignments, request = prepared
        self.validation_transcripts._items[(snapshot.source_id, snapshot.source_version)] = snapshot
        self.validation_facts._items.update({item.source_fact_id: item for item in facts})
        self.validation_claims._items.update({item.claim_id: item for item in claims})
        self.validation_alignments._items.update({item.alignment_id: item for item in alignments})
        run = self.validation_service.execute(request)
        self._persist_validation_findings(run, result.claims, source)
        upstream = UpstreamRun(run_id=run.validation_run_id, status="FAILED" if uncomparable_numeric else "SUCCEEDED", source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)
        workflow_log("DETERMINISTIC_VALIDATION", "DETERMINISTIC_VALIDATION_RESULT", outcome="SUCCESS" if upstream.status == "SUCCEEDED" else "ERROR", noteId=note_id, noteRevision=revision, runId=upstream.run_id, status=upstream.status, findingCount=len(run.findings))
        return upstream

    def _persist_uncomparable_numeric_findings(self, note_id, revision, claim_set_id, extraction, claims, source) -> bool:
        numeric_facts = tuple(fact for fact in extraction.facts if fact.numeric_value and fact.unit)
        if not numeric_facts:
            return False
        numeric_claims = tuple(value for claim in claims for value in claim.numeric_values)
        uncomparable = False
        run_id = f"validation-{claim_set_id}"
        for fact in numeric_facts:
            expected_unit = fact.unit.upper()
            compatible_units = {
                "CELSIUS": {"CELSIUS"},
                "MILLILITRE": {"MILLILITRE", "LITRE"},
                "LITRE": {"MILLILITRE", "LITRE"},
                "MILLIGRAM": {"MILLIGRAM", "GRAM"},
                "GRAM": {"MILLIGRAM", "GRAM"},
                "MMHG": {"MMHG"},
                "BEATS_PER_MINUTE": {"BEATS_PER_MINUTE"},
            }
            comparable = any(
                (value.unit_normalized or "").upper() in compatible_units.get(expected_unit, set())
                for value in numeric_claims
            )
            if comparable:
                continue
            uncomparable = True
            finding_id = f"review-{run_id}-NUM-006-{fact.source_fact_id}"
            if finding_id in self.review_service.repository.findings:
                continue
            severity, rationale = severity_for(origin="SPEC_005", rule_code="NUM-006")
            if numeric_claims:
                explanation = (
                    f"The source measurement {fact.numeric_value} {fact.unit} has no comparable note measurement. "
                    "The note value or unit could not be matched deterministically."
                )
            else:
                explanation = (
                    f"The source measurement {fact.numeric_value} {fact.unit} has no numeric value in the note. "
                    "Numeric comparison was not evaluable."
                )
            self.review_service.add_finding(ReviewFinding(
                reviewFindingId=finding_id,
                origin="SPEC_005",
                originRunId=run_id,
                originFindingId=f"{run_id}:NUM-006:{fact.source_fact_id}",
                noteId=note_id,
                noteRevision=revision,
                sourceId=source.source_id,
                sourceVersion=source.source_version,
                claimId=None,
                claimSpan=None,
                upstreamStatus="NOT_EVALUABLE",
                ruleCode="NUM-006",
                severity=severity,
                severityPolicyVersion=SEVERITY_POLICY_VERSION,
                severityRationale=rationale,
                explanation=explanation,
                evidence=self._source_evidence(source, fact.source_spans),
                state="OPEN",
                createdAt=datetime.now(timezone.utc),
            ))
        return uncomparable

    def coverage(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        workflow_log("SOURCE_COVERAGE", "SOURCE_COVERAGE_STARTED", noteId=note_id, noteRevision=revision, claimSetId=claim_set_id)
        note, source = self._source(note_id, revision)
        extraction = self.extraction_repository.get(f"source-facts-{claim_set_id}")
        request = CoverageRunRequest(
            contractVersion="COVERAGE-CONTRACT-v1", sourceId=source.source_id, sourceVersion=source.source_version,
            residentContext={"residentTestId": source.resident_test_id, "source": "SPEC_001_SOURCE_DOCUMENT", "trustLevel": "AUTHORITATIVE_TRANSCRIPT", "version": f"{source.source_id}:v{source.source_version}", "permittedUse": "TRANSCRIPT_EVIDENCE_ONLY"},
            sourceTextHash=source_text_hash(source.transcript_text), normalizationPolicy=extraction.normalization_policy,
            noteId=note_id, noteRevision=revision, sourceFactExtractionRunId=extraction.extraction_run_id,
            claimSetId=claim_set_id, rulesetVersion="COVERAGE-RULESET-v1", datasetVersion="COVERAGE-DATASET-v1",
            idempotencyKey=f"coverage:{note_id}:{revision}:{claim_set_id}",
        )
        run = self.coverage_service.execute(request)
        self._persist_coverage_findings(run, self.claim_sets.get(claim_set_id).claims, source)
        status = "SUCCEEDED" if getattr(run, "status", None) == "SUCCEEDED" else "FAILED"
        unresolved = getattr(getattr(run, "runtime_counts", None), "unresolved_source_items", 0)
        upstream = UpstreamRun(run_id=run.coverage_run_id, status=status, source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id, unresolved_source_items=unresolved)
        workflow_log("SOURCE_COVERAGE", "SOURCE_COVERAGE_RESULT", outcome="SUCCESS" if status == "SUCCEEDED" else "ERROR", noteId=note_id, noteRevision=revision, runId=upstream.run_id, status=status, findingCount=len(getattr(run, "findings", ()),), unresolvedSourceItemCount=unresolved)
        return upstream


class ReliabilityWorkflow:
    """Own all cross-component repositories and expose review verification ports."""

    def __init__(self, *, source_service, note_service, review_service, claim_provider=None, evidence_verifier=None, coverage_matcher=None):
        self.source_service = source_service
        self.note_repository = note_service.repository
        self.claim_repository = InMemoryClaimRepository()
        self.claim_results: dict[str, object] = {}
        self.claim_service = ClaimExtractionService(
            NursingNoteRevisionReader(self.note_repository, source_service),
            claim_provider or HeuristicClaimProvider(),
            repository=self.claim_repository,
        )
        self.extraction_repository = InMemorySourceFactExtractionRepository()
        self.claim_sets = InMemoryClaimSetRepository()
        self.coverage_runs = InMemoryCoverageRunRepository()
        self.coverage_service = SourceCoverageService(
            source_service.repository,
            self.extraction_repository,
            self.claim_sets,
            run_repository=self.coverage_runs,
            note_repository=self.note_repository,
            matcher=coverage_matcher,
        )
        self.evidence_runs = InMemoryVerificationRepository()
        self.evidence_service = VerificationService(
            source_service=source_service,
            note_repository=self.note_repository,
            claim_resolver=lambda claim_set_id: self.claim_repository.get_current_result_by_extraction_run_id(claim_set_id) if hasattr(self.claim_repository, "get_current_result_by_extraction_run_id") else self._claim_result(claim_set_id),
            verifier=evidence_verifier or OfflineSemanticEvidenceProvider(),
            repository=self.evidence_runs,
        )
        self.validation_runs = InMemoryValidationRunRepository()
        self.validation_transcripts = InMemoryTranscriptRepository()
        self.validation_facts = InMemorySourceFactRepository()
        self.validation_claims = InMemoryDeterministicClaimRepository()
        self.validation_alignments = InMemoryAlignmentRepository()
        self.validation_service = DeterministicValidationService(
            self.validation_transcripts,
            self.validation_facts,
            self.validation_claims,
            self.validation_alignments,
            self.validation_runs,
        )
        delegate = WorkflowVerificationPorts(
            source_service=source_service, note_repository=self.note_repository,
            review_service=review_service,
            claim_service=self.claim_service, evidence_service=self.evidence_service,
            coverage_service=self.coverage_service, validation_service=self.validation_service,
            validation_transcripts=self.validation_transcripts, validation_facts=self.validation_facts,
            validation_claims=self.validation_claims, validation_alignments=self.validation_alignments,
            validation_runs=self.validation_runs,
            extraction_repository=self.extraction_repository, claim_sets=self.claim_sets,
        )
        self.ports = ReferenceOnlyVerificationPorts(
            extract_claims=delegate.extract, verify_evidence=delegate.evidence,
            validate_deterministically=delegate.validation, read_coverage=delegate.coverage,
        )

    def _claim_result(self, claim_set_id: str):
        for result in reversed(getattr(self.claim_repository, "_results", {}).values()):
            if result.extraction_run_id == claim_set_id:
                return result
        return None


def _deterministic_records(source, note_id: str, revision: int, extraction: SourceFactExtractionResult, claims):
    """Translate comparable numeric records into the deterministic engine contract."""
    unit_map = {"CELSIUS": (MeasurementCategory.TEMPERATURE, Unit.CELSIUS), "ML": (MeasurementCategory.FLUID_INTAKE, Unit.MILLILITRE), "MILLILITRE": (MeasurementCategory.FLUID_INTAKE, Unit.MILLILITRE), "L": (MeasurementCategory.FLUID_INTAKE, Unit.LITRE), "LITRE": (MeasurementCategory.FLUID_INTAKE, Unit.LITRE), "MG": (MeasurementCategory.MEDICATION_QUANTITY, Unit.MILLIGRAM), "MILLIGRAM": (MeasurementCategory.MEDICATION_QUANTITY, Unit.MILLIGRAM), "G": (MeasurementCategory.MEDICATION_QUANTITY, Unit.GRAM), "GRAM": (MeasurementCategory.MEDICATION_QUANTITY, Unit.GRAM), "MMHG": (MeasurementCategory.BLOOD_PRESSURE, Unit.MMHG), "BEATS_PER_MINUTE": (MeasurementCategory.PULSE, Unit.BEATS_PER_MINUTE)}
    pairs = []
    for fact in extraction.facts:
        if not fact.numeric_value or not fact.unit or fact.unit.upper() not in unit_map:
            continue
        category, unit = unit_map[fact.unit.upper()]
        for claim in claims:
            if not claim.numeric_values:
                continue
            value = claim.numeric_values[0]
            claim_unit = (value.unit_normalized or "").upper()
            compatible_units = {
                "CELSIUS": {"CELSIUS"},
                "MILLILITRE": {"MILLILITRE", "LITRE"},
                "LITRE": {"MILLILITRE", "LITRE"},
                "MILLIGRAM": {"MILLIGRAM", "GRAM"},
                "GRAM": {"MILLIGRAM", "GRAM"},
                "MMHG": {"MMHG"},
                "BEATS_PER_MINUTE": {"BEATS_PER_MINUTE"},
            }
            if claim_unit in compatible_units.get(unit.value, set()):
                pairs.append((fact, claim, category, unit, value))
                break
    if not pairs:
        return None
    facts_out, claims_out, alignments = [], [], []
    for index, (fact, claim, category, unit, value) in enumerate(pairs, 1):
        ref = fact.source_spans[0]
        quoted = source.transcript_text[ref.start:ref.end]
        evidence_id = f"{fact.source_fact_id}:evidence"
        evidence = EvidenceReference(evidenceReferenceId=evidence_id, sourceId=source.source_id, sourceVersion=source.source_version, start=ref.start, end=ref.end, quotedText=quoted)
        approximation = "APPROXIMATE" if fact.approximation.value == "APPROXIMATE" or value.approximation else "EXACT"
        fact_id = f"dve-{fact.source_fact_id}"
        claim_id = f"dve-{claim.id}"
        alignment_id = f"dve-alignment-{index}"
        facts_out.append(DeterministicSourceFact(sourceFactId=fact_id, sourceId=source.source_id, sourceVersion=source.source_version, measurement={"category": category.value, "value": fact.numeric_value, "unit": unit.value, "approximation": approximation}, evidence=(evidence,)))
        claims_out.append(DeterministicClaim(claimId=claim_id, noteId=note_id, noteRevision=revision, measurement={"category": category.value, "value": str(value.normalized_decimal or value.raw).replace(",", "."), "unit": value.unit_normalized or unit.value, "approximation": approximation}, evidence=(evidence,)))
        alignments.append(Alignment(alignmentId=alignment_id, sourceFactId=fact_id, claimId=claim_id, status="ALIGNED"))
    request = ValidationRequest(rulesetVersion="DVE-RULESET-v1", sourceId=source.source_id, sourceVersion=source.source_version, noteId=note_id, noteRevision=revision, sourceFactIds=tuple(item.source_fact_id for item in facts_out), claimIds=tuple(item.claim_id for item in claims_out), alignmentIds=tuple(item.alignment_id for item in alignments))
    return TranscriptSnapshot(sourceId=source.source_id, sourceVersion=source.source_version, transcriptText=source.transcript_text), tuple(facts_out), tuple(claims_out), tuple(alignments), request


__all__ = ["ReliabilityWorkflow"]
