from __future__ import annotations

import pytest

from deterministic_validation.contracts import (
    Alignment,
    Claim,
    SourceFact,
    TranscriptSnapshot,
    ValidationRequest,
)
from deterministic_validation.errors import DeterministicValidationError
from deterministic_validation.repository import (
    InMemoryAlignmentRepository,
    InMemoryClaimRepository,
    InMemorySourceFactRepository,
    InMemoryTranscriptRepository,
    InMemoryValidationRunRepository,
)
from deterministic_validation.service import DeterministicValidationService


SOURCE_TEXT = "Temperatur 37,2 °C."


def evidence(ref_id: str = "evidence-1", *, version: int = 1, text: str = "37,2") -> dict[str, object]:
    return {
        "evidenceReferenceId": ref_id,
        "sourceId": "source-1",
        "sourceVersion": version,
        "start": 11,
        "end": 15,
        "quotedText": text,
    }


def request(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "rulesetVersion": "DVE-RULESET-v1",
        "sourceId": "source-1",
        "sourceVersion": 1,
        "noteId": "note-1",
        "noteRevision": 1,
        "sourceFactIds": ["fact-1"],
        "claimIds": ["claim-1"],
        "alignmentIds": ["alignment-1"],
    }
    result.update(overrides)
    return result


def make_service(*, claim_revision: int | None = 1, claim_note: str = "note-1", run_repository=None, raw_fact=None, source_repository=None) -> DeterministicValidationService:
    snapshot = TranscriptSnapshot(sourceId="source-1", sourceVersion=1, transcriptText=SOURCE_TEXT)
    fact = raw_fact or SourceFact(
        sourceFactId="fact-1", sourceId="source-1", sourceVersion=1,
        measurement={"category": "TEMPERATURE", "value": "37,2", "unit": "CELSIUS", "approximation": "EXACT"},
        evidence=(evidence_model(),),
    )
    claim = Claim(
        claimId="claim-1", noteId=claim_note, noteRevision=claim_revision,
        measurement={"category": "TEMPERATURE", "value": "37.2", "unit": "CELSIUS", "approximation": "EXACT"},
    )
    class RawFactRepository:
        def get(self, fact_id: str):
            return fact

    return DeterministicValidationService(
        source_repository or InMemoryTranscriptRepository([snapshot]),
        RawFactRepository() if raw_fact is not None else InMemorySourceFactRepository([fact]),
        InMemoryClaimRepository([claim]),
        InMemoryAlignmentRepository([Alignment(alignmentId="alignment-1", sourceFactId="fact-1", claimId="claim-1", status="ALIGNED")]),
        run_repository or InMemoryValidationRunRepository(),
        id_factory=lambda: "run-1",
    )


def evidence_model():
    from deterministic_validation.contracts import EvidenceReference
    return EvidenceReference.model_validate(evidence())


def test_service_returns_complete_success_metadata_and_persists_one_run() -> None:
    repository = InMemoryValidationRunRepository()
    result = make_service(run_repository=repository).execute(request())
    assert result.validation_run_id == "run-1"
    assert result.contract_version == "DVE-CONTRACT-v1"
    assert result.ruleset_version == "DVE-RULESET-v1"
    assert result.engine_version == "DVE-ENGINE-v1"
    assert len(result.input_digest) == 64
    assert result.findings == ()
    assert len(repository.runs) == 1


def test_service_allows_repeated_fact_claims_across_explicit_alignments() -> None:
    service = make_service()
    service.alignment_repository = InMemoryAlignmentRepository([
        Alignment(alignmentId="alignment-1", sourceFactId="fact-1", claimId="claim-1", status="ALIGNED"),
        Alignment(alignmentId="alignment-2", sourceFactId="fact-1", claimId="claim-1", status="ALIGNED"),
    ])
    result = service.execute(request(alignmentIds=["alignment-1", "alignment-2"]))
    assert result.findings == ()


def test_nullable_persisted_claim_revision_is_str002_not_success() -> None:
    result = make_service(claim_revision=None).execute(request())
    assert result.findings[0].rule_id == "STR-002"
    assert result.findings[0].outcome.value == "FAIL"


def test_wrong_note_revision_is_a_provenance_conflict_without_a_run() -> None:
    with pytest.raises(DeterministicValidationError) as captured:
        make_service(claim_revision=2).execute(request())
    assert captured.value.status_code == 409
    assert captured.value.payload.code.value == "PROVENANCE_CONFLICT"


def test_missing_source_version_is_a_404_without_a_run() -> None:
    with pytest.raises(DeterministicValidationError) as captured:
        make_service().execute(request(sourceVersion=2))
    assert captured.value.status_code == 404
    assert captured.value.payload.code.value in {"SOURCE_NOT_FOUND", "SOURCE_VERSION_NOT_FOUND"}


def test_missing_claim_is_a_typed_404() -> None:
    service = make_service()
    service.claim_repository = InMemoryClaimRepository([])
    with pytest.raises(DeterministicValidationError) as captured:
        service.execute(request())
    assert captured.value.status_code == 404
    assert captured.value.payload.code.value == "CLAIM_NOT_FOUND"


def test_invalid_request_is_schema_error_and_does_not_append() -> None:
    repository = InMemoryValidationRunRepository()
    with pytest.raises(DeterministicValidationError) as captured:
        make_service(run_repository=repository).execute(request(claimIds=[]))
    assert captured.value.status_code == 422
    assert captured.value.payload.code == "SCHEMA_ERROR"
    assert repository.runs == []


def test_repository_failure_is_dependency_unavailable() -> None:
    class BrokenRunRepository:
        def append(self, run):
            raise RuntimeError("storage offline")

    with pytest.raises(DeterministicValidationError) as captured:
        make_service(run_repository=BrokenRunRepository()).execute(request())
    assert captured.value.status_code == 503
    assert captured.value.payload.code.value == "DEPENDENCY_UNAVAILABLE"


def test_unexpected_engine_failure_is_internal_error_without_a_run() -> None:
    class BrokenEngine:
        def evaluate(self, *args, **kwargs):
            raise ValueError("unexpected")

    service = make_service()
    service.engine = BrokenEngine()
    with pytest.raises(DeterministicValidationError) as captured:
        service.execute(request())
    assert captured.value.status_code == 500
    assert captured.value.payload.code.value == "INTERNAL_ERROR"


def test_resolved_unsupported_category_is_provenance_conflict() -> None:
    unsupported = {
        "sourceFactId": "fact-1", "sourceId": "source-1", "sourceVersion": 1,
        "measurement": {"category": "UNKNOWN", "value": "1", "unit": "CELSIUS", "approximation": "EXACT"},
        "evidence": [evidence()],
    }
    with pytest.raises(DeterministicValidationError) as captured:
        make_service(raw_fact=unsupported).execute(request())
    assert captured.value.status_code == 409

