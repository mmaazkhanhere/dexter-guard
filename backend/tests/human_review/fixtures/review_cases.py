"""Stable synthetic German fixture manifest for HR-001 through HR-018."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewScenario:
    scenario_id: str
    title: str
    expected_outcome: str
    expected_audit_event: str
    source_id: str = "synthetic-source-001"
    source_version: int = 1
    note_id: str = "synthetic-note-001"
    note_revision: int = 1
    run_ids: tuple[str, ...] = ("claims-run-001", "evidence-run-001", "validation-run-001", "coverage-run-001")


SCENARIOS: tuple[ReviewScenario, ...] = (
    ReviewScenario("HR-001", "validated evidence display", "AVAILABLE evidence excerpt and deterministic severity", "FINDING_IMPORTED"),
    ReviewScenario("HR-002", "missing or invalid evidence", "no misleading evidence highlight", "FINDING_IMPORTED"),
    ReviewScenario("HR-003", "finding decision history", "immutable decision event with reviewer attribution", "FINDING_DECISION_RECORDED"),
    ReviewScenario("HR-004", "accepted correction", "one immutable successor revision", "NOTE_REVISION_CREATED"),
    ReviewScenario("HR-005", "stale manual revision", "STALE_REVISION and no write", "NOTE_CREATED"),
    ReviewScenario("HR-006", "claim feedback", "approvalEligible is false", "CLAIM_REVERIFICATION_RECORDED"),
    ReviewScenario("HR-007", "latest full verification", "current revision component runs only", "FULL_VERIFICATION_RECORDED"),
    ReviewScenario("HR-008", "critical approval guard", "APPROVAL_PRECONDITION_FAILED", "FULL_VERIFICATION_RECORDED"),
    ReviewScenario("HR-009", "rejection after failure", "auditable REJECTED disposition", "NOTE_REJECTED"),
    ReviewScenario("HR-010", "audit history", "ordered immutable events", "NOTE_APPROVED"),
    ReviewScenario("HR-011", "unsupported suggestion", "UNUSABLE correction cannot apply", "SUGGESTION_RECORDED"),
    ReviewScenario("HR-012", "source version mismatch", "INVALID evidence and no excerpt", "FINDING_IMPORTED"),
    ReviewScenario("HR-013", "non-critical adjudication", "ADJUDICATED immutable decision", "FINDING_DECISION_RECORDED"),
    ReviewScenario("HR-014", "failed component", "approval blocked", "FULL_VERIFICATION_RECORDED"),
    ReviewScenario("HR-015", "concurrent approval conflict", "stale request writes no disposition", "NOTE_REVISION_CREATED"),
    ReviewScenario("HR-016", "eligible approval", "APPROVED disposition and audit event", "NOTE_APPROVED"),
    ReviewScenario("HR-017", "post-verification edit", "successor awaits a new full verification", "NOTE_REVISION_CREATED"),
    ReviewScenario("HR-018", "unresolved source item", "approval blocked", "FULL_VERIFICATION_RECORDED"),
)


SYNTHETIC_TRANSCRIPT = "Bewohnerin A: Temperatur 37,2 Grad. Mobilisation mit Unterstützung."
SYNTHETIC_NOTE = "Temperatur 37,2 Grad dokumentiert."
