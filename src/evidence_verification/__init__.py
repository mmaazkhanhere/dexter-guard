"""Runtime contracts and deterministic integrity checks for Spec 004."""

from .contracts import (
    EvidenceFinding,
    EvidenceQuote,
    EvidenceRole,
    EvidenceStatus,
    SourceSpan,
    VerificationRunRequest,
    VerificationRunSucceeded,
)
from .validation import (
    ImmutableClaimReference,
    IdempotencyKeyConflictError,
    VerificationIntegrityError,
    canonical_request_digest,
    validate_claim_references,
    validate_idempotency_replay,
    validate_successful_run,
)

__all__ = [
    "EvidenceFinding",
    "EvidenceQuote",
    "EvidenceRole",
    "EvidenceStatus",
    "ImmutableClaimReference",
    "IdempotencyKeyConflictError",
    "SourceSpan",
    "VerificationIntegrityError",
    "VerificationRunRequest",
    "VerificationRunSucceeded",
    "canonical_request_digest",
    "validate_claim_references",
    "validate_idempotency_replay",
    "validate_successful_run",
]
