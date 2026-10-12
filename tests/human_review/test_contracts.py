from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from human_review.contracts import (
    FindingDecisionRequest,
    FullNoteVerification,
    FullVerificationRequest,
    ReviewFinding,
)


def test_openapi_declares_all_implemented_review_routes():
    contract_path = Path(__file__).parents[2] / "specs" / "007-human-review-and-audit" / "contracts" / "review-audit.openapi.yaml"
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    paths = document["paths"]
    assert "/api/v1/reviews/{noteId}/full-verifications" in paths
    assert "/api/v1/reviews/{noteId}/findings/{findingId}/claim-reverification" in paths
    assert paths["/api/v1/reviews/{noteId}/approve"]["post"]["responses"]["201"]
    assert paths["/api/v1/reviews/{noteId}/reject"]["post"]["responses"]["201"]


def test_request_models_reject_unknown_fields_and_enforce_conditionals():
    with pytest.raises(ValidationError):
        FullVerificationRequest(expectedRevision=1, reviewerLabel="r", idempotencyKey="k", extra="nope")
    with pytest.raises(ValidationError):
        FindingDecisionRequest(expectedRevision=1, kind="SUGGESTION_ACCEPTED", reviewerLabel="r", idempotencyKey="k")
    with pytest.raises(ValidationError):
        FindingDecisionRequest(expectedRevision=1, kind="DISPUTED", reviewerLabel="r", idempotencyKey="k")


def test_upstream_findings_require_provenance_ids():
    with pytest.raises(ValidationError):
        ReviewFinding(
            reviewFindingId="f-1", origin="SPEC_004", noteId="n-1", noteRevision=1,
            sourceId="s-1", sourceVersion=1, severity="MAJOR",
            severityPolicyVersion="REVIEW_SEVERITY-v1", severityRationale="test",
            explanation="test", evidence={"availability": "MISSING", "spans": [], "excerpts": []},
            state="OPEN", createdAt=datetime.now(timezone.utc),
        )


def test_terminal_verification_backfills_completed_at_for_legacy_callers():
    verification = FullNoteVerification(
        fullVerificationId="v-1", noteId="n-1", noteRevision=1,
        source={"sourceId": "s-1", "sourceVersion": 1}, claimSetId="claims-1",
        evidenceRunId="e-1", deterministicValidationRunId="d-1", coverageRunId="c-1",
        componentStatuses=[
            {"component": "CLAIM_EXTRACTION", "runId": "claims-run", "status": "SUCCEEDED"},
            {"component": "EVIDENCE_VERIFICATION", "runId": "e-1", "status": "SUCCEEDED"},
            {"component": "DETERMINISTIC_VALIDATION", "runId": "d-1", "status": "SUCCEEDED"},
            {"component": "SOURCE_COVERAGE", "runId": "c-1", "status": "SUCCEEDED"},
        ],
        status="VALID", idempotencyKey="k-1", requestDigest="digest-1",
        createdAt=datetime.now(timezone.utc),
    )
    assert verification.completed_at == verification.created_at
