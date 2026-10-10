"""Source transcript ingestion and evidence-reference foundation."""

from .contracts import (
    CreateSourceRequest,
    CreateSourceVersionRequest,
    ResolvedSourceSpan,
    SourceDocument,
    SourceSpan,
)
from .app import app, create_app
from .repository import InMemorySourceRepository, SourceRepository
from .service import SourceIngestionService

__all__ = [
    "CreateSourceRequest",
    "CreateSourceVersionRequest",
    "app",
    "create_app",
    "InMemorySourceRepository",
    "ResolvedSourceSpan",
    "SourceDocument",
    "SourceIngestionService",
    "SourceRepository",
    "SourceSpan",
]
