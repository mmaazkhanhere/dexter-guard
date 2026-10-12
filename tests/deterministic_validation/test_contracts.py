from __future__ import annotations

import pytest
from pydantic import ValidationError

from deterministic_validation.contracts import (
    Alignment,
    AlignmentStatus,
    Approximation,
    BloodPressureMeasurement,
    Claim,
    EvidenceReference,
    MeasurementCategory,
    ReasonCode,
    ScalarMeasurement,
    ValidationFinding,
    ValidationRequest,
    ValidationRun,
)


def scalar(category: str = "TEMPERATURE", value: str = "37,2", unit: str = "CELSIUS") -> dict[str, object]:
    return {"category": category, "value": value, "unit": unit, "approximation": "EXACT"}


def request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rulesetVersion": "DVE-RULESET-v1",
        "sourceId": "source-1",
        "sourceVersion": 1,
        "noteId": "note-1",
        "noteRevision": 1,
        "sourceFactIds": ["fact-1"],
        "claimIds": ["claim-1"],
        "alignmentIds": ["alignment-1"],
    }
    payload.update(overrides)
    return payload


def evidence(reference_id: str = "evidence-1") -> dict[str, object]:
    return {
        "evidenceReferenceId": reference_id,
        "sourceId": "source-1",
        "sourceVersion": 1,
        "start": 0,
        "end": 4,
        "quotedText": "37,2",
    }


def test_validation_request_is_strict_and_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="unique IDs"):
        ValidationRequest.model_validate(request(sourceFactIds=["fact-1", "fact-1"]))

    with pytest.raises(ValidationError):
        ValidationRequest.model_validate({key: value for key, value in request().items() if key != "claimIds"})

    with pytest.raises(ValidationError):
        ValidationRequest.model_validate(request(claimIds=[""]))


def test_measurement_union_preserves_typed_blood_pressure_value() -> None:
    measurement = BloodPressureMeasurement.model_validate(
        {"category": "BLOOD_PRESSURE", "value": {"systolic": "120", "diastolic": 80}, "unit": "MMHG", "approximation": "EXACT"}
    )
    assert measurement.value.systolic == "120"
    assert measurement.unit.value == "MMHG"


def test_claim_revision_is_required_but_nullable_for_persisted_malformed_records() -> None:
    payload = {
        "claimId": "claim-1",
        "noteId": "note-1",
        "noteRevision": None,
        "measurement": scalar(),
        "evidence": [],
    }
    claim = Claim.model_validate(payload)
    assert claim.note_revision is None

    with pytest.raises(ValidationError):
        Claim.model_validate({key: value for key, value in payload.items() if key != "noteRevision"})


def test_evidence_reference_ids_are_unique_within_each_resolved_record() -> None:
    with pytest.raises(ValidationError, match="unique"):
        from deterministic_validation.contracts import SourceFact

        SourceFact.model_validate(
            {
                "sourceFactId": "fact-1",
                "sourceId": "source-1",
                "sourceVersion": 1,
                "measurement": scalar(),
                "evidence": [
                    {"evidenceReferenceId": "same", "sourceId": "source-1", "sourceVersion": 1, "start": 0, "end": 1, "quotedText": "a"},
                    {"evidenceReferenceId": "same", "sourceId": "source-1", "sourceVersion": 1, "start": 1, "end": 2, "quotedText": "b"},
                ],
            }
        )


def test_alignment_status_is_explicit_and_does_not_infer_semantics() -> None:
    alignment = Alignment.model_validate(
        {"alignmentId": "alignment-1", "sourceFactId": "fact-1", "claimId": "claim-1", "status": "AMBIGUOUS"}
    )
    assert alignment.status is AlignmentStatus.AMBIGUOUS


def test_finding_contract_closes_rule_and_conditional_fields() -> None:
    with pytest.raises(ValidationError, match="pair identifiers"):
        ValidationFinding.model_validate(
            {
                "ruleId": "ALIGN-001",
                "ruleVersion": "1",
                "rulesetVersion": "DVE-RULESET-v1",
                "outcome": "NOT_EVALUABLE",
                "sourceFactId": None,
                "claimId": "claim-1",
                "alignmentId": "alignment-1",
                "evidenceReferenceIds": [],
                "expectedValue": None,
                "observedValue": None,
                "unit": None,
                "requiresReview": True,
                "reasonCode": "ALIGNMENT_AMBIGUOUS",
                "message": "Alignment is ambiguous.",
            }
        )

    finding = ValidationFinding.model_validate(
        {
            "ruleId": "NUM-001",
            "ruleVersion": "1",
            "rulesetVersion": "DVE-RULESET-v1",
            "outcome": "FAIL",
            "sourceFactId": "fact-1",
            "claimId": "claim-1",
            "alignmentId": "alignment-1",
            "evidenceReferenceIds": ["evidence-1"],
            "expectedValue": "37.2",
            "observedValue": "38.2",
            "unit": "CELSIUS",
            "requiresReview": True,
            "reasonCode": ReasonCode.NUMERIC_MISMATCH,
            "message": "Temperature differs.",
        }
    )
    assert finding.model_dump(by_alias=True)["requiresReview"] is True


def test_run_requires_complete_traceability_metadata() -> None:
    run = ValidationRun.model_validate(
        {
            "validationRunId": "run-1",
            "sourceId": "source-1",
            "sourceVersion": 1,
            "noteId": "note-1",
            "noteRevision": 1,
            "inputDigest": "a" * 64,
            "engineVersion": "DVE-ENGINE-v1",
            "contractVersion": "DVE-CONTRACT-v1",
            "rulesetVersion": "DVE-RULESET-v1",
            "findings": [],
        }
    )
    assert run.input_digest == "a" * 64

