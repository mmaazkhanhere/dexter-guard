"""Spec 002 nursing-note generation domain."""

from .adapters import (
    DeterministicNursingNoteAdapter,
    GenerationAdapter,
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
from .repository import InMemoryNoteRepository, NoteRepository
from .service import NursingNoteService

__all__ = [
    "CandidateNursingFact",
    "DeterministicNursingNoteAdapter",
    "ExternalOrigin",
    "GenerateRequest",
    "GenerationAdapter",
    "ImportRequest",
    "InMemoryNoteRepository",
    "NoteRepository",
    "NoteResponse",
    "NursingFact",
    "NursingNoteService",
    "UnavailableGenerationAdapter",
]
