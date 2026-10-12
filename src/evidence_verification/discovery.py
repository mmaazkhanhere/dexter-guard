"""Advisory, source-only candidate evidence preparation for the verifier port."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


_NORMALIZED_FIELDS = (
    "subject",
    "predicate",
    "object",
    "polarity",
    "certainty",
    "attribution",
    "temporal_text",
    "category",
)


@dataclass(frozen=True)
class CandidateEvidence:
    """Immutable provider input that preserves the upstream claim object."""

    claim: object
    claim_id: str
    claim_text: str
    normalized_attributes: Mapping[str, object]
    source_text: str

    @property
    def id(self) -> str:
        """Compatibility alias for upstream claim repositories and test fakes."""

        return self.claim_id

    def __getattr__(self, name: str) -> object:
        # Existing provider implementations can still read upstream attributes
        # while the wrapper exposes an explicit, bounded candidate contract.
        return getattr(self.claim, name)


def discover_candidate_evidence(claims: Sequence[object], source_text: str) -> tuple[CandidateEvidence, ...]:
    """Prepare full-source advisory candidates without deciding a status.

    The PoC deliberately keeps short transcripts whole. Retrieval absence,
    ranking, and candidate text never become evidence or a classification.
    """

    if not isinstance(source_text, str) or not source_text:
        raise ValueError("source_text must be a non-empty immutable string")
    candidates: list[CandidateEvidence] = []
    for claim in claims:
        claim_id = str(getattr(claim, "id", ""))
        claim_text = getattr(claim, "claim_text", None)
        if not claim_id or not isinstance(claim_text, str) or not claim_text:
            raise ValueError("resolved claims must expose non-empty id and claim_text")
        attributes: dict[str, object] = {}
        for field in _NORMALIZED_FIELDS:
            value = getattr(claim, field, None)
            if value is not None:
                attributes[field] = getattr(value, "value", value)
        candidates.append(
            CandidateEvidence(
                claim=claim,
                claim_id=claim_id,
                claim_text=claim_text,
                normalized_attributes=attributes,
                source_text=source_text,
            )
        )
    return tuple(candidates)

