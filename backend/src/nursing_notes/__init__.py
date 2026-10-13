"""Spec 002 nursing-note generation domain."""

from .adapters import (
    DeterministicNursingNoteAdapter,
    GenerationAdapter,
    OpenAICompatibleGenerationAdapter,
    UnavailableGenerationAdapter,
)
from .contracts import (
    CandidateNursingFact,
    ExternalOrigin,
    GenerateRequest,
    ImportRequest,
    NoteResponse,
    NursingFact,
)
from .repository import InMemoryNoteRepository, NoteRepository, SQLiteNoteRepository
from .observability import GenerationMetrics, GenerationMetricsSnapshot
from .service import NursingNoteService

__all__ = [
    "CandidateNursingFact",
    "DeterministicNursingNoteAdapter",
    "ExternalOrigin",
    "GenerateRequest",
    "GenerationAdapter",
    "GenerationMetrics",
    "GenerationMetricsSnapshot",
    "ImportRequest",
    "InMemoryNoteRepository",
    "NoteRepository",
    "SQLiteNoteRepository",
    "NoteResponse",
    "NursingFact",
    "NursingNoteService",
    "OpenAICompatibleGenerationAdapter",
    "UnavailableGenerationAdapter",
]
