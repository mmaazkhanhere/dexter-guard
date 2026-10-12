"""Immutable German acceptance cases mapped to EV-001 through EV-014."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Spec004Case:
    case_id: str
    source_text: str
    claim_text: str
    expected_status: str | None
    discrepancies: tuple[str, ...] = ()
    span_text: str | None = None
    expected_run_status: str = "SUCCEEDED"
    failure_code: str | None = None
    mode: str = "normal"


SPEC_004_CASES: tuple[Spec004Case, ...] = (
    Spec004Case("EV-001", "Die Patientin wirkt ruhig.", "Patientin wirkt ruhig.", "SUPPORTED", span_text="wirkt ruhig"),
    Spec004Case("EV-002", "Der Blutdruck ist stabil.", "Patientin hat Übelkeit.", "UNSUPPORTED"),
    Spec004Case("EV-003", "Der Patient klagt über starke Schmerzen.", "Patient hat keine Schmerzen.", "CONTRADICTED", span_text="starke Schmerzen"),
    Spec004Case("EV-004", "Der Patient hat keine Schmerzen.", "Patient hat Schmerzen.", "CONTRADICTED", ("NEGATION",), "keine Schmerzen"),
    Spec004Case("EV-005", "Vielleicht Schmerzen beim Umlagern.", "Patient hat Schmerzen beim Umlagern.", "UNCERTAIN", ("CERTAINTY",), "Vielleicht Schmerzen beim Umlagern"),
    Spec004Case("EV-006", "Der Patient berichtet Schwindel.", "Patient hat Schwindel.", "UNCERTAIN", ("ATTRIBUTION",), "berichtet Schwindel"),
    Spec004Case("EV-007", "Der Patient wirkt müde.", "Patient hat eine Depression.", "UNSUPPORTED", ("CLINICAL_INFERENCE",)),
    Spec004Case("EV-008", "Die Patientin klagt über Atemnot.", "Patientin berichtet Dyspnoe.", "SUPPORTED", span_text="Atemnot"),
    Spec004Case("EV-009", "Druckgefühl, Ursache unklar.", "Patient hat ein Druckgefühl.", "UNCERTAIN", span_text="Druckgefühl, Ursache unklar"),
    Spec004Case("EV-010", "Der Patient wirkt ruhig.", "Patient wirkt ruhig.", None, span_text="wirkt ruhig", expected_run_status="FAILED_EVIDENCE_INTEGRITY", failure_code="INVALID_EVIDENCE", mode="quote-mismatch"),
    Spec004Case("EV-011", "Der Patient wirkt ruhig.", "Patient wirkt ruhig.", None, expected_run_status="FAILED_VALIDATION", failure_code="SOURCE_NOT_FOUND", mode="stale-source"),
    Spec004Case("EV-012", "Der Patient wirkt ruhig.", "Patient wirkt ruhig.", None, expected_run_status="FAILED_VERIFIER", failure_code="MALFORMED_VERIFIER_OUTPUT", mode="malformed"),
    Spec004Case("EV-013", "Keine starken Schmerzen.", "Keine Schmerzen.", "UNCERTAIN", ("NEGATION",), "Keine starken Schmerzen"),
    Spec004Case("EV-014", "Die Patientin ist wach und orientiert.", "Patientin hat Schmerzen.", "UNSUPPORTED"),
)

