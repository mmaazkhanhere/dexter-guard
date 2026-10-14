"""Runtime contracts and deterministic integrity checks for Spec 004."""

from .contracts import (
    Discrepancy,
    EvidenceFinding,
    EvidenceQuote,
    EvidenceRole,
    EvidenceStatus,
    SourceSpan,
    VerificationRunRequest,
    VerificationRunFailed,
    VerificationRunSucceeded,
    VerificationFailure,
    VerificationRun,
)
from .provider import (
    MalformedVerifierOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    StructuredVerifierAdapter,
    VerifierCandidateFinding,
    VerifierResponse,
)
from .openai_compatible import OpenAICompatibleEvidenceVerifier
from .repository import (
    IdempotencyReservation,
    InMemoryVerificationRepository,
    SQLiteVerificationRepository,
    VerificationRepositoryError,
)
from .service import VerificationService, VerificationServiceError
from .observability import InMemoryVerificationLogger, VerificationMetrics, VerificationMetricsSnapshot
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
from .spans import SourceSpanValidationError, SourceTextIndex, derive_source_quote
from .discovery import CandidateEvidence, discover_candidate_evidence

__all__ = [
    "EvidenceFinding",
    "Discrepancy",
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
    "VerificationRunFailed",
    "VerificationRunSucceeded",
    "VerificationFailure",
    "VerificationRun",
    "MalformedVerifierOutputError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "StructuredVerifierAdapter",
    "VerifierCandidateFinding",
    "VerifierResponse",
    "OpenAICompatibleEvidenceVerifier",
    "IdempotencyReservation",
    "InMemoryVerificationRepository",
    "SQLiteVerificationRepository",
    "VerificationRepositoryError",
    "VerificationService",
    "VerificationServiceError",
    "InMemoryVerificationLogger",
    "VerificationMetrics",
    "VerificationMetricsSnapshot",
    "canonical_request_digest",
    "validate_claim_references",
    "validate_idempotency_replay",
    "validate_successful_run",
    "SourceSpanValidationError",
    "SourceTextIndex",
    "derive_source_quote",
    "CandidateEvidence",
    "discover_candidate_evidence",
]
