"""Server-side configuration for the provider-agnostic LLM boundary."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv

from nursing_notes.adapters import GenerationAdapter, OpenAICompatibleGenerationAdapter, UnavailableGenerationAdapter
from evidence_verification.openai_compatible import OpenAICompatibleEvidenceVerifier


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


def evidence_verifier_from_environment(values: Mapping[str, str] | None = None) -> object | None:
    """Build the optional live evidence verifier from server-side settings.

    Verification-specific variables take precedence.  The existing ``LLM_*``
    variables remain a convenient fallback for deployments using one model for
    both note generation and evidence verification.
    """
    environment = values if values is not None else os.environ
    api_key = environment.get("VERIFICATION_LLM_API_KEY", environment.get("LLM_API_KEY", "")).strip()
    model = environment.get("VERIFICATION_LLM_MODEL", environment.get("LLM_MODEL", "")).strip()
    base_url = environment.get("VERIFICATION_LLM_BASE_URL", environment.get("LLM_BASE_URL", "https://api.openai.com/v1")).strip()
    if not api_key or not model or not base_url:
        return None
    try:
        # Verification may evaluate several extracted claims in one response.
        # Keep its bounded allowance independent from note generation's shorter
        # timeout unless an explicit verification override is supplied.
        timeout_seconds = float(environment.get("VERIFICATION_LLM_TIMEOUT_SECONDS", "45"))
        max_output_tokens = int(environment.get("VERIFICATION_LLM_MAX_TOKENS", "4096"))
        input_cost = _optional_float(environment.get("VERIFICATION_LLM_INPUT_COST_PER_1K"))
        output_cost = _optional_float(environment.get("VERIFICATION_LLM_OUTPUT_COST_PER_1K"))
    except ValueError as error:
        raise ValueError("verification LLM timeout, output limit, and pricing values must be numeric") from error
    return OpenAICompatibleEvidenceVerifier(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_output_tokens=max_output_tokens,
        input_cost_per_1k=input_cost,
        output_cost_per_1k=output_cost,
    )


def _optional_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    return float(value)

