"""Contract-first extraction of atomic claims from immutable nursing-note revisions."""

from .models import (
    Attribution,
    Certainty,
    Claim,
    ClaimCategory,
    EvidenceSourceReference,
    ExtractionEmpty,
    ExtractionError,
    ExtractionErrorCode,
    ExtractionFailed,
    ExtractionResult,
    ExtractionStatus,
    ExtractionSucceeded,
    MedicationDetails,
    NumericRange,
    NumericValue,
    Polarity,
    TextSpan,
)
from .repository import ClaimRepository, InMemoryClaimRepository, SQLiteClaimRepository
from .service import ClaimExtractionService
from .spans import SpanValidator
from .validator import ClaimValidator

__all__ = [
    "Attribution",
    "Certainty",
    "Claim",
    "ClaimCategory",
    "ClaimExtractionService",
    "ClaimValidator",
    "ClaimRepository",
    "EvidenceSourceReference",
    "ExtractionEmpty",
    "ExtractionError",
    "ExtractionErrorCode",
    "ExtractionFailed",
    "ExtractionResult",
    "ExtractionStatus",
    "ExtractionSucceeded",
    "InMemoryClaimRepository",
    "MedicationDetails",
    "NumericRange",
    "NumericValue",
    "Polarity",
    "SQLiteClaimRepository",
    "SpanValidator",
    "TextSpan",
]
