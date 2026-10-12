from __future__ import annotations

import json
from pathlib import Path

from .fixtures import SPEC_004_CASES


def test_versioned_manifest_matches_ev_fixture_ids_and_policy() -> None:
    path = Path("specs/004-evidence-verification/fixtures/ev-001-014-v1.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["manifestVersion"] == "SPEC004_CRITICAL_CASES-v1"
    assert manifest["annotationPolicyVersion"] == "EVIDENCE_ANNOTATION-v1"
    assert manifest["evidenceStatusPolicyVersion"] == "EVIDENCE_STATUS-v1"
    assert [item["caseId"] for item in manifest["cases"]] == [case.case_id for case in SPEC_004_CASES]
    for item, case in zip(manifest["cases"], SPEC_004_CASES, strict=True):
        assert item["sourceText"] == case.source_text
        assert item["claimText"] == case.claim_text
        assert item["expectedStatus"] == case.expected_status
        assert tuple(item["requiredDiscrepancies"]) == case.discrepancies


def test_development_report_is_versioned_and_contains_all_required_metrics() -> None:
    path = Path("specs/004-evidence-verification/evaluation/spec004-development-evaluation-v1.json")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["reportSchemaVersion"] == "SPEC004_DEVELOPMENT_EVALUATION-v1"
    assert report["annotationPolicyVersion"] == "EVIDENCE_ANNOTATION-v1"
    assert report["evidenceStatusPolicyVersion"] == "EVIDENCE_STATUS-v1"
    assert report["classification"]["exactMatches"] == report["classification"]["total"] == report["totalClaims"]
    assert report["criticalErrorRecall"]["eligibleCriticalCases"] > 0
    assert report["supportedClaimFalsePositiveRate"]["predictedSupported"] > 0
    assert report["evidenceGroundingValidity"]["findingsRequiringGrounding"] > 0

