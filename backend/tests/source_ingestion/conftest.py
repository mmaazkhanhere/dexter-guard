from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from source_ingestion.app import create_app
from source_ingestion.repository import InMemorySourceRepository
from source_ingestion.service import SourceIngestionService


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "source-ingestion" / "valid-german-transcript.json"


@pytest.fixture
def valid_payload() -> dict[str, str]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def repository() -> InMemorySourceRepository:
    return InMemorySourceRepository()


@pytest.fixture
def service(repository: InMemorySourceRepository) -> SourceIngestionService:
    return SourceIngestionService(repository=repository)


@pytest.fixture
def client(service: SourceIngestionService) -> TestClient:
    return TestClient(create_app(service))
