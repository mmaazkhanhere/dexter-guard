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
from human_review.contracts import EvidenceDisplay, NoteSpan, ReviewFinding
from human_review.ports import ReferenceOnlyVerificationPorts, UpstreamRun
from human_review.policy import severity_for
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

    provider_version = "heuristic-claim-provider-v1"
    model_version = None
    prompt_version = "claim-extraction-heuristic-v1"

    _sentences = re.compile(r"[^.!?\r\n]+(?:[.!?]|$)")
    _number = re.compile(r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>°?C|ml|l|mg|g|mmHg)", re.IGNORECASE)

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
            statement_span = make_text_span(note_text, start, end)
            lower = statement.casefold()
            polarity = "NEGATED" if re.search(r"\b(?:kein|keine|keinen|nicht|verneint|ohne)\b", lower) else "AFFIRMED"
            certainty_match = re.search(r"\b(?:möglicherweise|moeglicherweise|vielleicht|eventuell|vermutlich|scheint)\w*\b", lower)
            certainty = "UNCERTAIN" if certainty_match else "CERTAIN"
            attribution = "UNSPECIFIED"
            category = "OBSERVATION"
            if re.search(r"\b(?:schmerz|schmerzen|schwindel|übelkeit|uebelkeit|müde|muede|atemnot|husten)\w*\b", lower):
                category = "SYMPTOM"
            number = self._number.search(statement)
            numeric_values: list[dict[str, object]] = []
            if number:
                category = "NUTRITION_HYDRATION" if number.group("unit").casefold() in {"ml", "l"} else "MEASUREMENT"
                value_start = start + number.start("value")
                value_end = start + number.end("value")
                unit_start = start + number.start("unit")
                unit_end = start + number.end("unit")
                unit_raw = number.group("unit")
                unit_normalized = {
                    "ml": "MILLILITRE", "l": "LITRE", "mg": "MILLIGRAM", "g": "GRAM",
                    "mmhg": "MMHG", "c": "CELSIUS", "°c": "CELSIUS",
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
                "id": f"{revision_id}:c{len(claims) + 1}",
                "noteRevisionId": revision_id,
                "residentTestId": resident_id,
                "ordinal": len(claims) + 1,
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
            claims.append(claim)
        return {"claims": claims}


class HeuristicEvidenceProvider:
    """Source-bound verifier used by the synthetic workflow when no remote verifier is configured."""

    model_id = "heuristic-evidence-verifier"
    model_version = "heuristic-evidence-v1"
    prompt_version = "evidence-verification-heuristic-v1"
    prompt_hash = "sha256:evidence-verification-heuristic-v1"

    def verify(self, *, claims, source_text: str, run_id: str, source_id: str | None = None, source_version: int | None = None):
        findings = []
        for candidate in claims:
            claim_text = str(getattr(candidate, "claim_text", "")).strip()
            start = source_text.find(claim_text)
            if start >= 0 and source_id and source_version:
                spans = [{"sourceId": source_id, "sourceVersion": source_version, "start": start, "end": start + len(claim_text)}]
                findings.append({"claimId": candidate.id, "status": "SUPPORTED", "explanation": "The claim text is present in the immutable source.", "sourceSpans": spans})
            else:
                findings.append({"claimId": candidate.id, "status": "UNSUPPORTED", "explanation": "The claim could not be located in the immutable source.", "sourceSpans": []})
        return {"findings": findings}


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
        return UpstreamRun(
            run_id=result.extraction_run_id,
            status="SUCCEEDED" if result.status in {ExtractionStatus.SUCCEEDED, ExtractionStatus.EMPTY} else "FAILED",
            source_id=source.source_id, source_version=source.source_version,
            note_id=note_id, note_revision=revision, claim_set_id=claim_set_id,
        )

    def evidence(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
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
        return UpstreamRun(run_id=run.verification_run_id, status=status, source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)

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
            severity = "CRITICAL" if finding.status.value == "CONTRADICTED" else "MAJOR"
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
                severityPolicyVersion="REVIEW_SEVERITY-v1",
                severityRationale="Evidence-verification status requires human review.",
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
            severity, rationale = severity_for(origin="SPEC_005", rule_code=finding.rule_id)
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
                claimId=finding.claim_id.removeprefix("dve-") if finding.claim_id else None,
                claimSpan=self._claim_span(claims, finding.claim_id),
                upstreamStatus=getattr(finding.outcome, "value", finding.outcome),
                ruleCode=finding.rule_id,
                severity=severity,
                severityPolicyVersion="REVIEW_SEVERITY-v1",
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
                severityPolicyVersion="REVIEW_SEVERITY-v1",
                severityRationale=rationale,
                explanation=f"{getattr(finding.status, 'value', finding.status)}: {finding.suggestion}",
                evidence=self._source_evidence(source, finding.source_spans, finding.source_quotes),
                state="OPEN",
                createdAt=datetime.now(timezone.utc),
            ))

    def validation(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
        note, source = self._source(note_id, revision)
        result = self.claim_service.repository.get_current_result(f"{note_id}:r{revision}")
        extraction = self.extraction_repository.get(f"source-facts-{claim_set_id}")
        if result is None or result.extraction_run_id != claim_set_id:
            raise LookupError("CLAIM_SET_NOT_FOUND")
        prepared = _deterministic_records(source, note_id, revision, extraction, result.claims)
        if prepared is None:
            return UpstreamRun(run_id=f"validation-{claim_set_id}", status="SUCCEEDED", source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)
        snapshot, facts, claims, alignments, request = prepared
        self.validation_transcripts._items[(snapshot.source_id, snapshot.source_version)] = snapshot
        self.validation_facts._items.update({item.source_fact_id: item for item in facts})
        self.validation_claims._items.update({item.claim_id: item for item in claims})
        self.validation_alignments._items.update({item.alignment_id: item for item in alignments})
        run = self.validation_service.execute(request)
        self._persist_validation_findings(run, result.claims, source)
        return UpstreamRun(run_id=run.validation_run_id, status="SUCCEEDED", source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id)

    def coverage(self, note_id: str, revision: int, claim_set_id: str) -> UpstreamRun:
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
        return UpstreamRun(run_id=run.coverage_run_id, status=status, source_id=source.source_id, source_version=source.source_version, note_id=note_id, note_revision=revision, claim_set_id=claim_set_id, unresolved_source_items=unresolved)


class ReliabilityWorkflow:
    """Own all cross-component repositories and expose review verification ports."""

    def __init__(self, *, source_service, note_service, review_service):
        self.source_service = source_service
        self.note_repository = note_service.repository
        self.claim_repository = InMemoryClaimRepository()
        self.claim_results: dict[str, object] = {}
        self.claim_service = ClaimExtractionService(
            NursingNoteRevisionReader(self.note_repository, source_service),
            HeuristicClaimProvider(),
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
        )
        self.evidence_runs = InMemoryVerificationRepository()
        self.evidence_service = VerificationService(
            source_service=source_service,
            note_repository=self.note_repository,
            claim_resolver=lambda claim_set_id: self.claim_repository.get_current_result_by_extraction_run_id(claim_set_id) if hasattr(self.claim_repository, "get_current_result_by_extraction_run_id") else self._claim_result(claim_set_id),
            verifier=HeuristicEvidenceProvider(),
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
    unit_map = {"CELSIUS": (MeasurementCategory.TEMPERATURE, Unit.CELSIUS), "ML": (MeasurementCategory.FLUID_INTAKE, Unit.MILLILITRE), "MILLILITRE": (MeasurementCategory.FLUID_INTAKE, Unit.MILLILITRE), "L": (MeasurementCategory.FLUID_INTAKE, Unit.LITRE), "LITRE": (MeasurementCategory.FLUID_INTAKE, Unit.LITRE), "MG": (MeasurementCategory.MEDICATION_QUANTITY, Unit.MILLIGRAM), "MILLIGRAM": (MeasurementCategory.MEDICATION_QUANTITY, Unit.MILLIGRAM), "G": (MeasurementCategory.MEDICATION_QUANTITY, Unit.GRAM), "GRAM": (MeasurementCategory.MEDICATION_QUANTITY, Unit.GRAM), "MMHG": (MeasurementCategory.BLOOD_PRESSURE, Unit.MMHG)}
    pairs = []
    for fact in extraction.facts:
        if not fact.numeric_value or not fact.unit or fact.unit.upper() not in unit_map:
            continue
        category, unit = unit_map[fact.unit.upper()]
        for claim in claims:
            if not claim.numeric_values:
                continue
            value = claim.numeric_values[0]
            if (value.unit_normalized or "").upper() == unit.value:
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
        claims_out.append(DeterministicClaim(claimId=claim_id, noteId=note_id, noteRevision=revision, measurement={"category": category.value, "value": str(value.normalized_decimal or value.raw).replace(",", "."), "unit": unit.value, "approximation": approximation}, evidence=(evidence,)))
        alignments.append(Alignment(alignmentId=alignment_id, sourceFactId=fact_id, claimId=claim_id, status="ALIGNED"))
    request = ValidationRequest(rulesetVersion="DVE-RULESET-v1", sourceId=source.source_id, sourceVersion=source.source_version, noteId=note_id, noteRevision=revision, sourceFactIds=tuple(item.source_fact_id for item in facts_out), claimIds=tuple(item.claim_id for item in claims_out), alignmentIds=tuple(item.alignment_id for item in alignments))
    return TranscriptSnapshot(sourceId=source.source_id, sourceVersion=source.source_version, transcriptText=source.transcript_text), tuple(facts_out), tuple(claims_out), tuple(alignments), request


__all__ = ["ReliabilityWorkflow"]
