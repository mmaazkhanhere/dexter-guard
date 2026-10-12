from __future__ import annotations

from .contracts import FullNoteVerification, ReviewFinding


class ReviewServiceError(RuntimeError):
    pass


class ApprovalEligibilityPolicy:
    version = "REVIEW_APPROVAL-v1"

    @classmethod
    def check(cls, *, latest_revision: int, requested_revision: int, verification: FullNoteVerification | None, findings: list[ReviewFinding]) -> None:
        if requested_revision != latest_revision:
            raise ReviewServiceError("STALE_REVISION")
        if verification is None or verification.status != "VALID" or verification.note_revision != latest_revision:
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if any(f.severity == "CRITICAL" and f.state in {"OPEN", "STALE"} for f in findings if f.note_revision == latest_revision):
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
        if any(status.status != "SUCCEEDED" for status in verification.component_statuses):
            raise ReviewServiceError("APPROVAL_PRECONDITION_FAILED")
