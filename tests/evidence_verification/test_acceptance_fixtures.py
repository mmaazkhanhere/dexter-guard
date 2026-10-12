from __future__ import annotations

from types import SimpleNamespace

import pytest

from evidence_verification import VerificationService
from .fixtures import SPEC_004_CASES, Spec004Case


class FixtureSourceRepository:
    def __init__(self, case: Spec004Case) -> None:
        self.case = case

    def get(self, source_id: str, source_version: int) -> object:
        if source_id != self.case.case_id or source_version != 1:
            raise LookupError("immutable source version not found")
        return SimpleNamespace(
            source_id=self.case.case_id,
            source_version=1,
            resident_test_id="resident-1",
            transcript_text=self.case.source_text,
        )


class FixtureClaimRepository:
    def __init__(self, case: Spec004Case) -> None:
        self.case = case

    def get(self, extraction_run_id: str) -> object:
        return SimpleNamespace(
            status="SUCCEEDED",
            extraction_run_id=extraction_run_id,
            claims=(SimpleNamespace(
                id=f"{self.case.case_id}:claim",
                note_revision_id="note-1:r1",
                resident_test_id="resident-1",
                claim_text=self.case.claim_text,
            ),),
        )


class FixtureVerifier:
    model_id = "spec004-fixture-verifier"
    model_version = "fixture-2026-10"
    prompt_version = "verification-v1"
    prompt_hash = "sha256:spec004-fixture"

    def __init__(self, case: Spec004Case) -> None:
        self.case = case

    def verify(self, *, claims, source_text: str, run_id: str) -> object:
        if self.case.mode == "malformed":
            return {"findings": [{"claimId": claims[0].id, "status": "SUPPORTED"}]}
        span = None
        if self.case.span_text is not None:
            start = source_text.index(self.case.span_text)
            span = {"sourceId": self.case.case_id, "sourceVersion": 1, "start": start, "end": start + len(self.case.span_text)}
        finding: dict[str, object] = {
            "claimId": claims[0].id,
            "status": self.case.expected_status or "SUPPORTED",
            "explanation": f"Fixture explanation for {self.case.case_id}.",
            "discrepancies": list(self.case.discrepancies),
        }
        if span is not None:
            finding["sourceSpans"] = [span]
        if self.case.mode == "quote-mismatch":
            finding["evidenceQuotes"] = [{"span": span, "text": "nicht aus der Quelle", "evidenceRole": "SUPPORTING"}]
        return {"findings": [finding]}


def make_request(case: Spec004Case) -> dict[str, object]:
    source_version = 2 if case.mode == "stale-source" else 1
    return {
        "sourceId": case.case_id,
        "sourceVersion": source_version,
        "noteId": "note-1",
        "noteRevision": 1,
        "claimSetId": f"{case.case_id}:claims",
        "idempotencyKey": f"{case.case_id}:idempotency",
        "claims": [{"claimId": f"{case.case_id}:claim", "residentTestId": "resident-1"}],
    }


def make_service(case: Spec004Case) -> VerificationService:
    return VerificationService(
        source_repository=FixtureSourceRepository(case),
        claim_repository=FixtureClaimRepository(case),
        verifier=FixtureVerifier(case),
        id_factory=lambda: f"{case.case_id}:run",
        correlation_factory=iter((f"{case.case_id}:correlation", f"{case.case_id}:trace")).__next__,
    )


@pytest.mark.parametrize("case", SPEC_004_CASES, ids=lambda case: case.case_id)
def test_ev_fixture_has_policy_relevant_expected_behavior(case: Spec004Case) -> None:
    result = make_service(case).verify(make_request(case))

    assert result.status == case.expected_run_status
    if case.expected_run_status != "SUCCEEDED":
        assert result.failure.code == case.failure_code
        assert not hasattr(result, "findings")
        return

    finding = result.findings[0]
    assert finding.claim_id == f"{case.case_id}:claim"
    assert finding.status.value == case.expected_status
    assert finding.policy_version == "EVIDENCE_ANNOTATION-v1"
    assert {item.value for item in finding.discrepancies} == set(case.discrepancies)
    if case.span_text is None:
        assert finding.source_spans == ()
    else:
        assert finding.evidence_quotes[0].text == case.span_text

