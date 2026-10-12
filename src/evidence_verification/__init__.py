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
    IdempotencyBinding,
    IdempotencyKeyConflictError,
    SqliteIdempotencyRegistry,
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
    "IdempotencyBinding",
    "IdempotencyKeyConflictError",
    "SqliteIdempotencyRegistry",
    "SourceSpan",
    "VerificationIntegrityError",
    "VerificationRunRequest",
    "VerificationRunSucceeded",
    "canonical_request_digest",
    "validate_claim_references",
    "validate_idempotency_replay",
    "validate_successful_run",
]
