from __future__ import annotations

from .contracts import FullNoteVerification, ReviewDecision, ReviewFinding


class ReviewServiceError(RuntimeError):
    pass


class ApprovalEligibilityPolicy:
    version = "REVIEW_APPROVAL-v1"

    @classmethod
    def check(cls, *, latest_revision: int, requested_revision: int, verification: FullNoteVerification | None, findings: list[ReviewFinding], decisions: list[ReviewDecision] | None = None, source: tuple[str, int] | None = None) -> None:
        if requested_revision != latest_revision:
            raise ReviewServiceError("STALE_REVISION")
        if verification is None or verification.status != "VALID" or verification.note_revision != latest_revision:
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if source is not None and (verification.source.source_id, verification.source.source_version) != source:
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if verification.evidence_run_id == "unavailable" or verification.deterministic_validation_run_id == "unavailable" or verification.coverage_run_id == "unavailable":
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        expected_runs = {"EVIDENCE_VERIFICATION": verification.evidence_run_id, "DETERMINISTIC_VALIDATION": verification.deterministic_validation_run_id, "SOURCE_COVERAGE": verification.coverage_run_id}
        if any(item.run_id != expected_runs.get(item.component, item.run_id) for item in verification.component_statuses if item.component in expected_runs):
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if verification.coverage_unresolved_source_items:
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if any(f.severity == "CRITICAL" and f.state in {"OPEN", "STALE"} for f in findings if f.note_revision == latest_revision):
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if any(status.status != "SUCCEEDED" for status in verification.component_statuses):
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        current_findings = [f for f in findings if f.note_revision == latest_revision]
        if decisions is not None:
            decided = {d.finding_id for d in decisions if d.note_revision == latest_revision}
            if any(f.review_finding_id not in decided for f in current_findings):
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
