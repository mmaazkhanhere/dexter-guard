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
        if verification.claim_set_id in {"", "unavailable"}:
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
        if any(status.status != "SUCCEEDED" for status in verification.component_statuses):
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        current_findings = [f for f in findings if f.note_id == verification.note_id and f.note_revision == latest_revision]
        current_decisions = [d for d in (decisions or []) if d.note_id == verification.note_id and d.note_revision == latest_revision]
        latest_by_finding: dict[str, ReviewDecision] = {}
        for decision in current_decisions:
            latest_by_finding[decision.finding_id] = decision
        for finding in current_findings:
            if finding.state not in {"OPEN", "STALE"}:
                continue
            decision = latest_by_finding.get(finding.review_finding_id)
            if decision is None or decision.outcome not in {"ADJUDICATED", "RESOLVED"}:
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if decisions is not None:
            decided = {d.finding_id for d in current_decisions}
            if any(f.review_finding_id not in decided for f in current_findings):
                raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
            for finding in current_findings:
                decision = latest_by_finding.get(finding.review_finding_id)
                if decision is None:
                    raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
                if finding.severity != "CRITICAL" and decision.outcome not in {"ADJUDICATED", "RESOLVED"}:
                    raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
