"""Typed, synthetic-only first-time product demonstration contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nursing_notes.contracts import NoteResponse
from source_ingestion.contracts import SourceDocument


class DemoStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: Literal["INSPECT", "VERIFY", "CORRECT", "REVERIFY", "APPROVE"]
    title: str = Field(min_length=1)
    instruction: str = Field(min_length=1)


class FounderDemoScenario(BaseModel):
    """A newly persisted, deliberately flawed synthetic review scenario."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    scenario_id: Literal["founder-walkthrough-v1"] = Field(default="founder-walkthrough-v1", alias="scenarioId")
    scenario_version: Literal["v1"] = Field(default="v1", alias="scenarioVersion")
    synthetic_only: Literal[True] = Field(default=True, alias="syntheticOnly")
    source: SourceDocument
    note: NoteResponse
    corrected_note: str = Field(alias="correctedNote", min_length=1)
    steps: tuple[DemoStep, ...]
