from __future__ import annotations

from types import SimpleNamespace

import pytest

from evidence_verification import EvidenceStatus, VerificationService


class SourceRepo:
    def __init__(self, text: str = "Patient verneint Schmerzen.", resident: str = "resident-1") -> None:
        self.source = SimpleNamespace(
            source_id="source-1",
            source_version=1,
            resident_test_id=resident,
            transcript_text=text,
        )

    def get(self, source_id: str, source_version: int) -> object:
        if (source_id, source_version) != (self.source.source_id, self.source.source_version):
            raise LookupError("missing source")
        return self.source


class ClaimRepo:
    def __init__(self, claim_text: str = "Patient hat keine Schmerzen.", note_revision_id: str = "note-1:r1") -> None:
        claim = SimpleNamespace(
            id="claim-1",
            note_revision_id=note_revision_id,
            resident_test_id="resident-1",
            claim_text=claim_text,
        )
        self.result = SimpleNamespace(status="SUCCEEDED", extraction_run_id="extract-1", claims=(claim,))

    def get(self, extraction_run_id: str) -> object:
        return self.result


class FakeVerifier:
    model_id = "fake-model"
    model_version = "fake-1"
    prompt_version = "verification-v1"
    prompt_hash = "sha256:test"

    def __init__(self, output_factory):
        self.output_factory = output_factory
        self.calls = 0

    def verify(self, *, claims, source_text, run_id):
        self.calls += 1
        return self.output_factory(source_text)


def request(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "sourceId": "source-1",
        "sourceVersion": 1,
        "noteId": "note-1",
        "noteRevision": 1,
        "claimSetId": "extract-1",
        "idempotencyKey": "key-1",
        "claims": [{"claimId": "claim-1", "residentTestId": "resident-1"}],
    }
    value.update(overrides)
    return value


def span(text: str, source: str) -> dict[str, object]:
    start = source.index(text)
    return {"sourceId": "source-1", "sourceVersion": 1, "start": start, "end": start + len(text)}


def service(verifier: FakeVerifier, *, source: SourceRepo | None = None, claims: ClaimRepo | None = None) -> VerificationService:
    return VerificationService(
        source_repository=source or SourceRepo(),
        claim_repository=claims or ClaimRepo(),
        verifier=verifier,
        id_factory=lambda: "run-1",
        correlation_factory=iter(("correlation-1", "trace-1")).__next__,
    )


def test_supported_finding_is_source_grounded_and_quote_is_derived() -> None:
    verifier = FakeVerifier(
        lambda source: {
            "findings": [{
                "claimId": "claim-1",
                "status": "SUPPORTED",
                "explanation": "Die Verneinung ist im Transkript belegt.",
                "sourceSpans": [span("verneint Schmerzen", source)],
                "discrepancies": [],
            }]
        }
    )
    result = service(verifier).verify(request())
    assert result.status == "SUCCEEDED"
    assert result.findings[0].status is EvidenceStatus.SUPPORTED
    assert result.findings[0].evidence_quotes[0].text == "verneint Schmerzen"


@pytest.mark.parametrize(
    ("text", "status", "discrepancy"),
    [
        ("Patient hat Schmerzen.", "CONTRADICTED", "NEGATION"),
        ("Vielleicht Schmerzen beim Umlagern.", "UNCERTAIN", "CERTAINTY"),
        ("Patient berichtet Schwindel.", "UNCERTAIN", "ATTRIBUTION"),
    ],
)
def test_german_qualifier_changes_are_preserved(text: str, status: str, discrepancy: str) -> None:
    source = SourceRepo(text=text)
    verifier = FakeVerifier(
        lambda source_text: {
            "findings": [{
                "claimId": "claim-1",
                "status": status,
                "explanation": "Qualifizierte Quelle.",
                "sourceSpans": [span(text, source_text)],
                "discrepancies": [discrepancy],
            }]
        }
    )
    result = service(verifier, source=source, claims=ClaimRepo(claim_text="Behauptung")).verify(request())
    assert result.status == "SUCCEEDED"
    assert result.findings[0].status.value == status
    assert discrepancy in {item.value for item in result.findings[0].discrepancies}


def test_unsupported_clinical_inference_succeeds_without_evidence_span() -> None:
    verifier = FakeVerifier(
        lambda source: {
            "findings": [{
                "claimId": "claim-1",
                "status": "UNSUPPORTED",
                "explanation": "Eine Diagnose wird nicht erwähnt.",
                "discrepancies": ["CLINICAL_INFERENCE"],
            }]
        }
    )
    result = service(verifier).verify(request())
    assert result.status == "SUCCEEDED"
    assert result.findings[0].source_spans == ()


def test_partial_negation_is_uncertain_with_valid_span() -> None:
    source = SourceRepo(text="Keine starken Schmerzen.")
    verifier = FakeVerifier(
        lambda source_text: {
            "findings": [{
                "claimId": "claim-1",
                "status": "UNCERTAIN",
                "explanation": "Die Negation beschränkt sich auf starke Schmerzen.",
                "sourceSpans": [span("Keine starken Schmerzen", source_text)],
                "discrepancies": ["NEGATION"],
            }]
        }
    )
    result = service(verifier, source=source).verify(request())
    assert result.status == "SUCCEEDED"
    assert result.findings[0].status is EvidenceStatus.UNCERTAIN


def test_malformed_provider_output_is_a_failed_run_and_not_uncertain() -> None:
    verifier = FakeVerifier(lambda _: {"findings": [{"claimId": "foreign", "status": "SUPPORTED"}]})
    result = service(verifier).verify(request())
    assert result.status == "FAILED_VERIFIER"
    assert result.failure.code == "MALFORMED_VERIFIER_OUTPUT"
    assert not hasattr(result, "findings")


def test_quote_mismatch_is_evidence_integrity_failure() -> None:
    verifier = FakeVerifier(
        lambda source: {
            "findings": [{
                "claimId": "claim-1",
                "status": "SUPPORTED",
                "explanation": "belegt",
                "sourceSpans": [span("verneint Schmerzen", source)],
                "evidenceQuotes": [{
                    "span": span("verneint Schmerzen", source),
                    "text": "erfundene Evidenz",
                    "evidenceRole": "SUPPORTING",
                }],
                "discrepancies": [],
            }]
        }
    )
    result = service(verifier).verify(request())
    assert result.status == "FAILED_EVIDENCE_INTEGRITY"


def test_idempotent_replay_does_not_invoke_provider_twice() -> None:
    verifier = FakeVerifier(
        lambda source: {
            "findings": [{
                "claimId": "claim-1",
                "status": "UNSUPPORTED",
                "explanation": "nicht im Text",
                "discrepancies": [],
            }]
        }
    )
    target = service(verifier)
    first = target.verify(request())
    replay = target.verify(request())
    assert first == replay
    assert verifier.calls == 1


def test_stale_claim_revision_fails_validation() -> None:
    verifier = FakeVerifier(lambda _: {"findings": []})
    result = service(verifier, claims=ClaimRepo(note_revision_id="note-1:r2")).verify(request())
    assert result.status == "FAILED_VALIDATION"
    assert result.failure.code == "CLAIM_REVISION_MISMATCH"
    assert verifier.calls == 0

