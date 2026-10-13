from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

import pytest
import yaml
from pydantic import ValidationError

from evidence_verification.contracts import EvidenceFinding, VerificationRunRequest, VerificationRunSucceeded
from evidence_verification.validation import (
    ImmutableClaimReference,
    IdempotencyKeyConflictError,
    SqliteIdempotencyRegistry,
    VerificationIntegrityError,
    canonical_request_digest,
    validate_claim_references,
    validate_idempotency_replay,
    validate_successful_run,
)


SOURCE = "Ärztin berichtet: keine starken Schmerzen."
START = SOURCE.index("keine")
END = START + len("keine starken Schmerzen")


def request(*claim_ids: str) -> VerificationRunRequest:
    return VerificationRunRequest.model_validate(
        {
            "sourceId": "source-1",
            "sourceVersion": 1,
            "noteId": "note-1",
            "noteRevision": 2,
            "claimSetId": "claim-set-1",
            "idempotencyKey": "key-1",
            "claims": [
                {"claimId": claim_id, "residentTestId": "resident-1"}
                for claim_id in claim_ids
            ],
        }
    )


def finding(claim_id: str = "c1", *, status: str = "SUPPORTED", start: int = START, end: int = END, text: str | None = None, role: str = "SUPPORTING") -> EvidenceFinding:
    spans = [] if status == "UNSUPPORTED" and start < 0 else [
        {"sourceId": "source-1", "sourceVersion": 1, "start": start, "end": end}
    ]
    quotes = [] if not spans else [
        {"span": spans[0], "text": SOURCE[start:end] if text is None else text, "evidenceRole": role}
    ]
    return EvidenceFinding.model_validate(
        {
            "claimId": claim_id,
            "status": status,
            "explanation": "review basis",
            "sourceSpans": spans,
            "evidenceQuotes": quotes,
            "discrepancies": [],
            "policyVersion": "EVIDENCE_ANNOTATION-v1",
            "verifierFinding": {"status": status, "explanation": "provider basis"},
            "deterministicRuleFindings": [{"code": "CONTRACT", "outcome": "PASS"}],
        }
    )


def run(
    *findings: EvidenceFinding,
    digest_request: VerificationRunRequest | None = None,
) -> VerificationRunSucceeded:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    digest_request = digest_request or request(*(item.claim_id for item in findings))
    return VerificationRunSucceeded.model_validate(
        {
            "verificationRunId": "run-1",
            "sourceId": "source-1",
            "sourceVersion": 1,
            "noteId": "note-1",
            "noteRevision": 2,
            "claimSetId": "claim-set-1",
            "idempotencyKey": "key-1",
            "inputDigest": canonical_request_digest(digest_request),
            "evidenceStatusPolicyVersion": "EVIDENCE_STATUS-v1",
            "annotationPolicyVersion": "EVIDENCE_ANNOTATION-v1",
            "modelId": "model-1",
            "modelVersion": "2026-01",
            "promptVersion": "verification-v1",
            "promptHash": "sha256:prompt",
            "correlationId": "correlation-1",
            "executionTraceId": "trace-1",
            "createdAt": now.isoformat(),
            "startedAt": (now + timedelta(seconds=1)).isoformat(),
            "completedAt": (now + timedelta(seconds=2)).isoformat(),
            "status": "SUCCEEDED",
            "findings": [item.model_dump(by_alias=True) for item in findings],
        }
    )


def test_request_rejects_duplicate_claim_ids() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        request("c1", "c1")


def test_claims_are_references_with_exact_immutable_ownership() -> None:
    immutable_claims = {
        "c1": ImmutableClaimReference("c1", "claim-set-1", "note-1", 2, "resident-1"),
    }
    validate_claim_references(request("c1"), immutable_claims, source_resident_test_id="resident-1")

    with pytest.raises(VerificationIntegrityError, match="unknown"):
        validate_claim_references(request("missing"), immutable_claims, source_resident_test_id="resident-1")
    mismatched_record = {"c1": ImmutableClaimReference("other-claim", "claim-set-1", "note-1", 2, "resident-1")}
    with pytest.raises(VerificationIntegrityError, match="mismatched claim record"):
        validate_claim_references(request("c1"), mismatched_record, source_resident_test_id="resident-1")
    stale = {"c1": ImmutableClaimReference("c1", "claim-set-1", "note-1", 1, "resident-1")}
    with pytest.raises(VerificationIntegrityError, match="different note revision"):
        validate_claim_references(request("c1"), stale, source_resident_test_id="resident-1")
    outside_set = {"c1": ImmutableClaimReference("c1", "other-set", "note-1", 2, "resident-1")}
    with pytest.raises(VerificationIntegrityError, match="claim set"):
        validate_claim_references(request("c1"), outside_set, source_resident_test_id="resident-1")
    wrong_resident = {"c1": ImmutableClaimReference("c1", "claim-set-1", "note-1", 2, "resident-2")}
    with pytest.raises(VerificationIntegrityError, match="resident"):
        validate_claim_references(request("c1"), wrong_resident, source_resident_test_id="resident-1")


def test_unknown_resident_is_rejected_without_resident_inference() -> None:
    payload = request("c1").model_dump(by_alias=True)
    payload["claims"][0]["residentTestId"] = "UNKNOWN"
    with pytest.raises(ValidationError, match="known synthetic resident"):
        VerificationRunRequest.model_validate(payload)


def test_claim_assertion_text_is_rejected_because_claims_are_references() -> None:
    payload = request("c1").model_dump(by_alias=True)
    payload["claims"][0]["assertion"] = "client-provided text"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        VerificationRunRequest.model_validate(payload)


def test_idempotency_replays_same_data_and_rejects_different_data() -> None:
    original = request("c1")
    digest = canonical_request_digest(original)
    assert validate_idempotency_replay(original, stored_input_digest=digest) == digest

    changed_payload = original.model_dump(by_alias=True)
    changed_payload["noteRevision"] = 3
    changed = VerificationRunRequest.model_validate(changed_payload)
    with pytest.raises(IdempotencyKeyConflictError, match="different request identity"):
        validate_idempotency_replay(changed, stored_input_digest=digest)


def test_sqlite_idempotency_registry_replays_or_rejects_atomically() -> None:
    registry = SqliteIdempotencyRegistry(sqlite3.connect(":memory:"))
    original = request("c1")

    created = registry.bind_or_replay(original, verification_run_id="run-1", run_payload="payload-1")
    replayed = registry.bind_or_replay(original, verification_run_id="run-2", run_payload="payload-2")

    assert created.created is True
    assert replayed.created is False
    assert replayed.verification_run_id == "run-1"
    assert replayed.input_digest == created.input_digest
    assert replayed.run_payload == "payload-1"

    changed_payload = original.model_dump(by_alias=True)
    changed_payload["sourceVersion"] = 2
    changed = VerificationRunRequest.model_validate(changed_payload)
    with pytest.raises(IdempotencyKeyConflictError, match="different request identity"):
        registry.bind_or_replay(changed, verification_run_id="run-3", run_payload="payload-3")


@pytest.mark.parametrize("findings", [(finding("c1"),), (finding("c1"), finding("c1")), (finding("c1"), finding("foreign"))])
def test_successful_run_requires_exact_distinct_claim_coverage(findings: tuple[EvidenceFinding, ...]) -> None:
    submitted_request = request("c1", "c2")
    with pytest.raises(VerificationIntegrityError, match="claim IDs|claimId"):
        validate_successful_run(submitted_request, run(*findings, digest_request=submitted_request), SOURCE)


def test_source_span_is_end_exclusive_and_quote_is_source_derived() -> None:
    valid = finding()
    validate_successful_run(request("c1"), run(valid), SOURCE)

    with pytest.raises(ValidationError, match="end-exclusive"):
        finding(end=START)
    with pytest.raises(VerificationIntegrityError, match="end-exclusive"):
        validate_successful_run(request("c1"), run(finding(end=len(SOURCE) + 1)), SOURCE)
    with pytest.raises(VerificationIntegrityError, match="exact immutable-source substring"):
        validate_successful_run(request("c1"), run(finding(text="invented quote")), SOURCE)


def test_successful_run_requires_the_canonical_input_digest() -> None:
    valid_run = run(finding())
    payload = valid_run.model_dump(by_alias=True)
    payload["inputDigest"] = "sha256:wrong"
    incorrect_digest_run = VerificationRunSucceeded.model_validate(payload)
    with pytest.raises(VerificationIntegrityError, match="inputDigest"):
        validate_successful_run(request("c1"), incorrect_digest_run, SOURCE)


def test_source_identity_must_match_the_requested_immutable_source() -> None:
    payload = finding().model_dump(by_alias=True)
    payload["sourceSpans"][0]["sourceId"] = "other-source"
    payload["evidenceQuotes"][0]["span"]["sourceId"] = "other-source"
    foreign_source_finding = EvidenceFinding.model_validate(payload)
    with pytest.raises(VerificationIntegrityError, match="different immutable source"):
        validate_successful_run(request("c1"), run(foreign_source_finding), SOURCE)


def test_unsupported_permits_only_non_supporting_context_or_no_evidence() -> None:
    no_evidence = finding(status="UNSUPPORTED", start=-1)
    validate_successful_run(request("c1"), run(no_evidence), SOURCE)

    context = finding(status="UNSUPPORTED", role="CONTEXT_NON_SUPPORTING")
    validate_successful_run(request("c1"), run(context), SOURCE)

    with pytest.raises(ValidationError, match="CONTEXT_NON_SUPPORTING"):
        finding(status="UNSUPPORTED", role="SUPPORTING")


def test_finding_requires_a_one_to_one_span_quote_pair() -> None:
    payload = finding().model_dump(by_alias=True)
    payload["evidenceQuotes"] = []
    with pytest.raises(ValidationError, match="require sourceSpans|one-to-one"):
        EvidenceFinding.model_validate(payload)


def test_openapi_exposes_required_execution_metadata_and_context_policy() -> None:
    contract = Path("specs/004-evidence-verification/contracts/verification-runs.openapi.yaml")
    document = yaml.safe_load(contract.read_text(encoding="utf-8"))
    schema = document["components"]["schemas"]
    required = schema["VerificationRunBase"]["required"]
    for name in ("modelId", "modelVersion", "promptVersion", "promptHash", "createdAt", "startedAt", "completedAt", "correlationId", "executionTraceId"):
        assert name in required
    assert schema["EvidenceFinding"]["properties"]["policyVersion"]["const"] == "EVIDENCE_ANNOTATION-v1"
    unsupported_then = schema["EvidenceFinding"]["allOf"][0]["then"]
    assert unsupported_then["properties"]["evidenceQuotes"]["items"]["properties"]["evidenceRole"]["const"] == "CONTEXT_NON_SUPPORTING"
    claim_input = schema["ClaimInput"]
    assert claim_input["required"] == ["claimId", "residentTestId"]
    assert "assertion" not in claim_input["properties"]
    assert claim_input["properties"]["residentTestId"]["pattern"] == "^[A-Za-z0-9][A-Za-z0-9._-]*$"
    assert claim_input["properties"]["residentTestId"]["not"]["const"] == "UNKNOWN"
    responses = document["paths"]["/api/v1/verification-runs"]["post"]["responses"]
    assert "202" not in responses
    assert responses["409"]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/IdempotencyConflictError"
    assert schema["IdempotencyConflictError"]["properties"]["code"]["const"] == "IDEMPOTENCY_KEY_CONFLICT"


def test_development_evaluation_report_schema_requires_the_measurement_gate() -> None:
    report = Path("specs/004-evidence-verification/contracts/development-evaluation-report.schema.json")
    schema = __import__("json").loads(report.read_text(encoding="utf-8"))
    assert schema["properties"]["reportSchemaVersion"]["const"] == "SPEC004_DEVELOPMENT_EVALUATION-v1"
    for metric in ("classification", "criticalErrorRecall", "supportedClaimFalsePositiveRate", "evidenceGroundingValidity"):
        assert metric in schema["required"]
