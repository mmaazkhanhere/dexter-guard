from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .contracts import (
    AnnotatedCandidateClaim, AnnotatedSourceFact, AnnotationProvenance, BenchmarkDataset, DatasetStatus,
    DatasetSplit, ErrorCategory, EvaluationCandidate, EvaluationCase, EvidenceStatus, GroundTruthError,
    SourceSnapshotReference, SourceSpan,
)


_CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _span(source_id: str, text: str, needle: str) -> SourceSpan:
    start = text.index(needle)
    return SourceSpan(sourceId=source_id, sourceVersion=1, start=start, end=start + len(needle))


def _case(index: int) -> EvaluationCase:
    categories = (
        ("SUPPORTED", None, "Die Bewohnerin berichtet über guten Schlaf.", "Schlaf war gut.", EvidenceStatus.SUPPORTED, "FAITHFULLY_COVERED"),
        ("UNSUPPORTED_FACT", ErrorCategory.UNSUPPORTED_FACT, "Die Bewohnerin berichtet keinen Schwindel.", "Schwindel vorhanden.", EvidenceStatus.UNSUPPORTED, "FAITHFULLY_COVERED"),
        ("EXPLICIT_CONTRADICTION", ErrorCategory.EXPLICIT_CONTRADICTION, "Die Bewohnerin verneint Schmerzen.", "Schmerzen vorhanden.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("NUMERIC_MISMATCH", ErrorCategory.NUMERIC_MISMATCH, "Die Temperatur beträgt 37,2 Grad Celsius.", "Die Temperatur beträgt 38,2 Grad Celsius.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("UNIT_MISMATCH", ErrorCategory.UNIT_MISMATCH, "Die Trinkmenge beträgt 500 ml.", "Die Trinkmenge beträgt 500 l.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("NEGATION_CHANGE", ErrorCategory.NEGATION_CHANGE, "Die Bewohnerin hat keinen Husten.", "Die Bewohnerin hat Husten.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("CERTAINTY_CHANGE", ErrorCategory.CERTAINTY_CHANGE, "Möglicherweise ist die Bewohnerin müde.", "Die Bewohnerin ist müde.", EvidenceStatus.UNCERTAIN, "FAITHFULLY_COVERED"),
        ("ATTRIBUTION_CHANGE", ErrorCategory.ATTRIBUTION_CHANGE, "Die Bewohnerin berichtet über Übelkeit.", "Die Pflegekraft berichtet über Übelkeit.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("CLINICAL_INFERENCE", ErrorCategory.CLINICAL_INFERENCE, "Die Bewohnerin wirkt blass.", "Die Bewohnerin hat eine Anämie.", EvidenceStatus.UNSUPPORTED, "FAITHFULLY_COVERED"),
        ("IMPORTANT_OMISSION", ErrorCategory.IMPORTANT_OMISSION, "Die Bewohnerin trank 300 ml Wasser.", "Die Bewohnerin war wach und ansprechbar.", EvidenceStatus.SUPPORTED, "OMITTED"),
        ("AMBIGUOUS_SOURCE", None, "Die Bewohnerin berichtet eventuell über Schwindel.", "Eventuell Schwindel berichtet.", EvidenceStatus.UNCERTAIN, "FAITHFULLY_COVERED"),
        ("HARMLESS_PARAPHRASE", None, "Die Bewohnerin ging mit Unterstützung zum Tisch.", "Die Bewohnerin wurde unterstützt zum Tisch begleitet.", EvidenceStatus.SUPPORTED, "FAITHFULLY_COVERED"),
    )
    tag, category, source_text, note_body, expected_status, coverage = categories[index % len(categories)]
    source_text = f"{source_text} Fall {index}."
    note_body = f"{note_body} Fall {index}."
    source_id = f"synthetic-source-{index:03d}"
    candidate_id = f"candidate-{index:03d}"
    scenario_id = f"scenario-{index:03d}"
    claim_id = f"claim-{index:03d}"
    source_hash = _sha(source_text)
    note_hash = _sha(note_body)
    source_ref = SourceSnapshotReference(
        sourceId=source_id, sourceVersion=1, sourceTextHash=source_hash,
        residentTestId=f"synthetic-resident-{index:03d}", language="de-DE",
        transcriptLocator=f"data/evaluation/008-v1/{scenario_id}/source.txt", transcriptText=source_text,
    )
    source_span = _span(source_id, source_text, source_text.split(".")[0] + ".")
    fact = AnnotatedSourceFact(
        sourceFactId=f"fact-{index:03d}", sourceSpans=(source_span,), expectation="IMPORTANT",
        applicableToCandidateIds="ALL", expectedEvidenceRelationship="DIRECT_SOURCE_SUPPORT",
        expectedCoverage=coverage,
    )
    claim_span = note_body
    claim = AnnotatedCandidateClaim(
        annotatedClaimId=f"annotated-{claim_id}", claimId=claim_id, statementReference=claim_span,
        expectedPrimaryStatus=expected_status, expectedDiscrepancies=((category.value if category else ""),) if category else (),
        expectedEvidenceSpans=(source_span,), scorable=True,
    )
    errors: tuple[GroundTruthError, ...] = ()
    claims: tuple[AnnotatedCandidateClaim, ...] = (claim,)
    if category is ErrorCategory.IMPORTANT_OMISSION:
        claims = ()
        errors = (GroundTruthError(
            errorId=f"error-{index:03d}", candidateId=candidate_id, affectedAnnotatedClaimId=None,
            affectedSourceFactId=fact.source_fact_id, category=category, severity="CRITICAL",
            expectedPrimaryStatus=None, requiredDiscrepancyOrRule="MISSING_EXPECTED_SOURCE_FACT",
            sourceEvidenceSpans=(source_span,), applicable=True,
        ),)
    elif category is not None:
        errors = (GroundTruthError(
            errorId=f"error-{index:03d}", candidateId=candidate_id, affectedAnnotatedClaimId=claim.annotated_claim_id,
            affectedSourceFactId=None, category=category, severity="CRITICAL" if index % 3 == 0 else "MAJOR",
            expectedPrimaryStatus=expected_status, requiredDiscrepancyOrRule=category.value,
            conflictingAttribute="semantic_attribute" if category in {ErrorCategory.NUMERIC_MISMATCH, ErrorCategory.UNIT_MISMATCH, ErrorCategory.NEGATION_CHANGE, ErrorCategory.CERTAINTY_CHANGE, ErrorCategory.ATTRIBUTION_CHANGE} else None,
            expectedValue=None, sourceEvidenceSpans=(source_span,), applicable=True,
        ),)
    if index % 25 == 0:
        second = GroundTruthError(
            errorId=f"error-{index:03d}-b", candidateId=candidate_id, affectedAnnotatedClaimId=claim.annotated_claim_id,
            affectedSourceFactId=None, category=ErrorCategory.OTHER, severity="MINOR",
            expectedPrimaryStatus=expected_status, requiredDiscrepancyOrRule="SECONDARY_DISCREPANCY",
            sourceEvidenceSpans=(source_span,), applicable=True,
        )
        errors = (*errors, second)
    split = DatasetSplit.DEVELOPMENT if index < 60 else DatasetSplit.VALIDATION if index < 80 else DatasetSplit.HELD_OUT
    tags = (tag, "MULTIPLE_ERRORS" if len(errors) > 1 else "SINGLE_ERROR", "FAMILY_UNIQUE")
    if tag in {"AMBIGUOUS_SOURCE", "HARMLESS_PARAPHRASE"}:
        tags = (*tags, tag)
    return EvaluationCase(
        scenarioId=scenario_id, scenarioFamilyId=f"family-{index:03d}", datasetVersion="008-v1", split=split,
        tags=tags, source=source_ref, referenceFacts=(fact,),
        candidateNotes=(EvaluationCandidate(
            candidateId=candidate_id, noteId=f"note-{index:03d}", noteRevision=1, noteBodyHash=note_hash,
            noteBody=note_body, origin="FIXTURE", annotatedClaims=claims, errorInstances=errors,
        ),),
        annotationProvenance=AnnotationProvenance(
            annotatorLabel="synthetic-benchmark-team", annotatedAt=_CREATED,
            reviewStatus="INDEPENDENTLY_REVIEWED", guideVersion="EVIDENCE_ANNOTATION-v1",
            rationaleLocator=f"data/evaluation/008-v1/{scenario_id}/annotation.json",
        ),
    )


def default_dataset() -> BenchmarkDataset:
    scenarios = tuple(_case(index) for index in range(100))
    draft = BenchmarkDataset(
        datasetId="synthetic-german-nursing-008", datasetVersion="008-v1", contentHash="0" * 64,
        status=DatasetStatus.ACCEPTED, language="de-DE", scenarioCount=len(scenarios),
        annotationGuideVersion="EVIDENCE_ANNOTATION-v1", evidenceStatusPolicyVersion="EVIDENCE_STATUS-v1",
        annotationPolicyVersion="EVIDENCE_ANNOTATION-v1", matchingPolicyVersion="EVALUATION_MATCHING-v1",
        createdAt=_CREATED, acceptedAt=_CREATED, scenarios=scenarios,
    )
    return draft.model_copy(update={"content_hash": _sha(draft.canonical_content())})

