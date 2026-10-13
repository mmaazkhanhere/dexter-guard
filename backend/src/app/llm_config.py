"""Server-side configuration for the provider-agnostic LLM boundary."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv

from nursing_notes.adapters import GenerationAdapter, OpenAICompatibleGenerationAdapter, UnavailableGenerationAdapter


def load_local_environment() -> None:
    """Load backend/.env for local runs without overriding real environment vars."""

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def generation_adapter_from_environment(
    values: Mapping[str, str] | None = None,
) -> GenerationAdapter:
    """Build the common chat adapter from server-side environment variables.

    Missing credentials intentionally produce the existing fail-closed adapter;
    importing the application must remain safe in tests and local offline mode.
    """

    environment = values if values is not None else os.environ
    api_key = environment.get("LLM_API_KEY", "").strip()
    model = environment.get("LLM_MODEL", "").strip()
    base_url = environment.get("LLM_BASE_URL", "https://api.openai.com/v1").strip()
    if not api_key or not model or not base_url:
        return UnavailableGenerationAdapter()
    try:
        timeout_seconds = float(environment.get("LLM_TIMEOUT_SECONDS", "30"))
    except ValueError as error:
        raise ValueError("LLM_TIMEOUT_SECONDS must be a positive number") from error
    return OpenAICompatibleGenerationAdapter(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )

