from datetime import datetime, timezone

import pytest

from source_ingestion.contracts import SourceDocument
from source_ingestion.repository import InMemorySourceRepository

from source_coverage.contracts import CoverageRunFailed, CoverageRunSucceeded
from source_coverage.extraction import HeuristicGermanSourceFactExtractor, source_text_hash
from source_coverage.provider import ProviderOutputError
from source_coverage.repository import (
    ClaimSetRecord,
    InMemoryClaimSetRepository,
    InMemoryCoverageRunRepository,
    InMemorySourceFactExtractionRepository,
)
from source_coverage.service import CoverageServiceError, SourceCoverageService
from tests.source_coverage.test_matching import claim


SOURCE_TEXT = "Frau Müller klagte über Schmerzen im linken Knie."


def make_service(*, note_revision: int = 1, matcher=None, run_id_prefix: str = "coverage"):
    source = SourceDocument(
        source_id="source-1", source_version=1, resident_test_id="resident-1", language="de-DE",
        transcript_text=SOURCE_TEXT, created_at=datetime.now(timezone.utc),
    )
    sources = InMemorySourceRepository()
    sources.create_initial(source)
    extraction = HeuristicGermanSourceFactExtractor().extract(source, extraction_run_id="extract-1")
    selected_claim = claim("Bewohnerin berichtet über linksseitige Knieschmerzen.")
    if note_revision != 1:
        selected_claim = selected_claim.model_copy(update={"note_revision_id": f"note-1:r{note_revision}"})
    claim_sets = InMemoryClaimSetRepository([
        ClaimSetRecord("claims-1", "note-1", note_revision, "resident-1", "source-1", 1, (selected_claim,)),
    ])
    service = SourceCoverageService(
        sources, InMemorySourceFactExtractionRepository([extraction]), claim_sets,
        run_repository=InMemoryCoverageRunRepository(), matcher=matcher,
        id_factory=iter((f"{run_id_prefix}-1", f"{run_id_prefix}-2", f"{run_id_prefix}-3")).__next__,
        correlation_factory=iter(("correlation-1", "correlation-2", "correlation-3")).__next__,
    )
    request = {
        "contractVersion": "COVERAGE-CONTRACT-v1", "sourceId": "source-1", "sourceVersion": 1,
        "residentContext": {"residentTestId": "resident-1", "source": "SPEC_001_SOURCE_DOCUMENT", "trustLevel": "AUTHORITATIVE_TRANSCRIPT", "version": "source-1:v1", "permittedUse": "TRANSCRIPT_EVIDENCE_ONLY"},
        "sourceTextHash": source_text_hash(SOURCE_TEXT), "normalizationPolicy": "NFC_CODEPOINTS",
        "noteId": "note-1", "noteRevision": note_revision, "sourceFactExtractionRunId": "extract-1", "claimSetId": "claims-1",
        "rulesetVersion": "COVERAGE-RULESET-v1", "datasetVersion": "synthetic-v1", "idempotencyKey": "key-1",
    }
    return service, request


def test_service_returns_immutable_success_with_coverage_counts_and_no_note_text():
    service, payload = make_service()
    result = service.execute(payload)
    assert isinstance(result, CoverageRunSucceeded)
    assert result.status.value == "SUCCEEDED"
    assert result.runtime_counts.extracted_expected_facts == 1
    assert result.runtime_counts.covered_expected_facts == 1
    assert result.findings == ()
    assert result.model_dump(mode="json", by_alias=True).get("transcriptText") is None


def test_idempotency_replays_same_run_and_conflicting_digest_is_rejected():
    service, payload = make_service()
    first = service.execute(payload)
    replay = service.execute(payload)
    assert first.coverage_run_id == replay.coverage_run_id
    assert len(service.run_repository.runs) == 1
    changed = dict(payload, datasetVersion="synthetic-v2")
    with pytest.raises(CoverageServiceError) as error:
        service.execute(changed)
    assert error.value.code == "IDEMPOTENCY_KEY_CONFLICT"
    assert error.value.status_code == 409


def test_cross_revision_claim_set_is_rejected_and_new_revision_creates_new_run():
    service, payload = make_service(note_revision=2)
    with pytest.raises(CoverageServiceError) as error:
        service.execute(dict(payload, noteRevision=1))
    assert error.value.code == "PROVENANCE_CONFLICT"
    result = service.execute(payload)
    assert result.note_revision == 2
    assert len(service.run_repository.runs) == 1


def test_provider_failure_is_terminal_failed_run_without_partial_findings():
    class BrokenMatcher:
        matcher_version = "broken-v1"
        last_retry_count = 1

        def match(self, facts, claims, *, run_id):
            raise ProviderOutputError("provider returned invalid JSON")

    service, payload = make_service(matcher=BrokenMatcher())
    result = service.execute(payload)
    assert isinstance(result, CoverageRunFailed)
    assert result.failure.code == "MALFORMED_PROVIDER_OUTPUT"
    assert len(service.run_repository.runs) == 1
