"""Service-level integrity checks that need request and immutable-source context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json

from .contracts import EvidenceFinding, VerificationRunRequest, VerificationRunSucceeded


class VerificationIntegrityError(ValueError):
    """Raised when an otherwise well-shaped result is unsafe to accept."""


class IdempotencyKeyConflictError(VerificationIntegrityError):
    """Raised when an idempotency key is reused for different request data."""


@dataclass(frozen=True)
class ImmutableClaimReference:
    """The provenance fields returned by the immutable Spec 003 claim repository."""

    claim_id: str
    claim_set_id: str
    note_id: str
    note_revision: int
    resident_test_id: str


def canonical_request_digest(request: VerificationRunRequest) -> str:
    """Return a stable digest for the semantic identity of a create-run request.

    Claim references are sorted because their order cannot change the requested
    verification work. The idempotency key itself is deliberately excluded: it
    is the lookup key bound to this digest, not input being verified.
    """

    identity = {
        "sourceId": request.source_id,
        "sourceVersion": request.source_version,
        "noteId": request.note_id,
        "noteRevision": request.note_revision,
        "claimSetId": request.claim_set_id,
        "claims": sorted(
            ({"claimId": claim.claim_id, "residentTestId": claim.resident_test_id} for claim in request.claims),
            key=lambda claim: claim["claimId"],
        ),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def validate_idempotency_replay(
    request: VerificationRunRequest,
    *,
    stored_input_digest: str,
) -> str:
    """Accept an exact replay or fail before work begins for a key collision."""

    incoming_digest = canonical_request_digest(request)
    if stored_input_digest != incoming_digest:
        raise IdempotencyKeyConflictError(
            "idempotency key is already bound to a different request identity"
        )
    return incoming_digest


def validate_claim_references(
    request: VerificationRunRequest,
    immutable_claims: Mapping[str, ImmutableClaimReference],
    *,
    source_resident_test_id: str,
) -> None:
    """Require every by-reference claim to resolve within the requested provenance.

    The repository owns assertion text and normalized attributes. This guard only
    validates identity and ownership and deliberately does not infer residents.
    """

    if source_resident_test_id == "UNKNOWN":
        raise VerificationIntegrityError("source resident must be a known synthetic resident")
    for requested_claim in request.claims:
        if requested_claim.resident_test_id != source_resident_test_id:
            raise VerificationIntegrityError("claim resident does not match the immutable source resident")
        record = immutable_claims.get(requested_claim.claim_id)
        if record is None:
            raise VerificationIntegrityError("claim reference is unknown")
        if record.claim_id != requested_claim.claim_id:
            raise VerificationIntegrityError("claim repository returned a mismatched claim record")
        if record.claim_set_id != request.claim_set_id:
            raise VerificationIntegrityError("claim reference is outside the requested claim set")
        if (record.note_id, record.note_revision) != (request.note_id, request.note_revision):
            raise VerificationIntegrityError("claim reference belongs to a different note revision")
        if record.resident_test_id != source_resident_test_id:
            raise VerificationIntegrityError("claim resident does not match the immutable source resident")


def _validate_finding_source(
    finding: EvidenceFinding,
    *,
    source_id: str,
    source_version: int,
    source_text: str,
) -> None:
    for span in finding.source_spans:
        if span.source_id != source_id or span.source_version != source_version:
            raise VerificationIntegrityError("source span references a different immutable source")
        if not 0 <= span.start < span.end <= len(source_text):
            raise VerificationIntegrityError("source span is outside the immutable source or is not end-exclusive")
    for quote in finding.evidence_quotes:
        span = quote.span
        if span.source_id != source_id or span.source_version != source_version:
            raise VerificationIntegrityError("evidence quote references a different immutable source")
        if not 0 <= span.start < span.end <= len(source_text):
            raise VerificationIntegrityError("evidence quote span is outside the immutable source or is not end-exclusive")
        if quote.text != source_text[span.start : span.end]:
            raise VerificationIntegrityError("evidence quote must equal its exact immutable-source substring")


def validate_successful_run(
    request: VerificationRunRequest,
    run: VerificationRunSucceeded,
    source_text: str,
) -> None:
    """Validate exact claim coverage and source-bound evidence before persistence.

    Python string indexing is Unicode code-point indexing, which is the published
    offset convention. This function deliberately performs no semantic inference.
    """

    if (run.source_id, run.source_version) != (request.source_id, request.source_version):
        raise VerificationIntegrityError("run source identity does not match the request")
    if (run.note_id, run.note_revision, run.claim_set_id) != (
        request.note_id,
        request.note_revision,
        request.claim_set_id,
    ):
        raise VerificationIntegrityError("run note or claim-set identity does not match the request")
    if run.idempotency_key != request.idempotency_key:
        raise VerificationIntegrityError("run idempotency key does not match the request")

    requested_ids = {claim.claim_id for claim in request.claims}
    finding_ids = [finding.claim_id for finding in run.findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise VerificationIntegrityError("finding claimId values must be distinct")
    if set(finding_ids) != requested_ids:
        raise VerificationIntegrityError("findings must cover exactly the submitted claim IDs")

    for finding in run.findings:
        _validate_finding_source(
            finding,
            source_id=request.source_id,
            source_version=request.source_version,
            source_text=source_text,
        )
