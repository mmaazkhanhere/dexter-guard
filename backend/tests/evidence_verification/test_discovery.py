from __future__ import annotations

from types import SimpleNamespace

from evidence_verification import CandidateEvidence, discover_candidate_evidence


def test_candidate_discovery_preserves_full_source_and_normalized_attributes() -> None:
    claim = SimpleNamespace(
        id="claim-1",
        claim_text="Patient hat keine Schmerzen.",
        subject="Patient",
        predicate="hat Schmerzen",
        polarity=SimpleNamespace(value="NEGATED"),
        certainty=None,
    )
    source = "Der Patient hat keine Schmerzen."

    candidates = discover_candidate_evidence((claim,), source)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert isinstance(candidate, CandidateEvidence)
    assert candidate.id == "claim-1"
    assert candidate.claim_text == claim.claim_text
    assert candidate.source_text == source
    assert candidate.normalized_attributes == {
        "subject": "Patient",
        "predicate": "hat Schmerzen",
        "polarity": "NEGATED",
    }
    assert candidate.claim is claim

