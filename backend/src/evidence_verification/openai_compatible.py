"""OpenAI-compatible structured evidence-verifier provider."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from openai import OpenAI

from nursing_notes.openai_compatible import _parse_json_object, _response_content


class ChatCompletionsClient(Protocol):
    class _Completions(Protocol):
        def create(self, **kwargs: Any) -> Any: ...

    class _Chat(Protocol):
        completions: _Completions

    chat: _Chat


class OpenAICompatibleEvidenceVerifier:
    """Call a compatible chat endpoint and expose provider usage telemetry."""

    model_version = "openai-compatible-v1"
    prompt_version = "evidence-verification-openai-compatible-v1"
    prompt_hash = "sha256:evidence-verification-openai-compatible-v1"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        input_cost_per_1k: float | None = None,
        output_cost_per_1k: float | None = None,
        client: ChatCompletionsClient | None = None,
    ) -> None:
        if not api_key.strip() or not base_url.strip() or not model.strip():
            raise ValueError("api_key, base_url, and model must not be blank")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if input_cost_per_1k is not None and input_cost_per_1k < 0:
            raise ValueError("input_cost_per_1k must not be negative")
        if output_cost_per_1k is not None and output_cost_per_1k < 0:
            raise ValueError("output_cost_per_1k must not be negative")
        self.model_id = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.input_cost_per_1k = input_cost_per_1k
        self.output_cost_per_1k = output_cost_per_1k
        self.client = client or OpenAI(api_key=api_key, base_url=self.base_url, timeout=timeout_seconds, max_retries=0)
        self.last_input_tokens: int | None = None
        self.last_output_tokens: int | None = None
        self.last_inference_cost: float | None = None

    def verify(
        self,
        *,
        claims: Sequence[object],
        source_text: str,
        run_id: str,
        source_id: str | None = None,
        source_version: int | None = None,
    ) -> object:
        self.last_input_tokens = None
        self.last_output_tokens = None
        self.last_inference_cost = None
        response = self.client.chat.completions.create(
            model=self.model_id,
            temperature=0,
            timeout=self.timeout_seconds,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(claims, source_text, run_id, source_id, source_version)},
            ],
        )
        self._capture_usage(getattr(response, "usage", None) or (response.get("usage") if isinstance(response, Mapping) else None))
        payload = _parse_json_object(_response_content(response))
        return payload

    def _capture_usage(self, usage: object | None) -> None:
        def value(*names: str) -> int | None:
            for name in names:
                item = usage.get(name) if isinstance(usage, Mapping) else getattr(usage, name, None)
                if item is not None:
                    try:
                        return max(0, int(item))
                    except (TypeError, ValueError):
                        return None
            return None

        self.last_input_tokens = value("prompt_tokens", "input_tokens")
        self.last_output_tokens = value("completion_tokens", "output_tokens")
        if self.last_input_tokens is not None and self.last_output_tokens is not None and self.input_cost_per_1k is not None and self.output_cost_per_1k is not None:
            self.last_inference_cost = (
                self.last_input_tokens / 1000 * self.input_cost_per_1k
                + self.last_output_tokens / 1000 * self.output_cost_per_1k
            )


_SYSTEM_PROMPT = """You are an evidence verifier for German nursing documentation.
Return only one JSON object with a findings array. Return exactly one finding for
each submitted claim ID. Use only the immutable transcript as evidence.
Each finding must contain:
{
  "claimId": "submitted claim ID",
  "status": "SUPPORTED|UNSUPPORTED|CONTRADICTED|UNCERTAIN",
  "explanation": "short explanation",
  "sourceSpans": [{"sourceId": "provided source ID", "sourceVersion": 1, "start": 0, "end": 1}],
  "evidenceQuotes": [],
  "discrepancies": ["NEGATION|CERTAINTY|ATTRIBUTION|CLINICAL_INFERENCE|OTHER"]
}
Use an empty sourceSpans array only for UNSUPPORTED claims. Character offsets
must be exact Python end-exclusive offsets into the supplied transcript.
"""


def _user_prompt(claims: Sequence[object], source_text: str, run_id: str, source_id: str | None, source_version: int | None) -> str:
    claim_payload = []
    for claim in claims:
        if hasattr(claim, "model_dump"):
            claim_payload.append(claim.model_dump(mode="json", by_alias=True))
        else:
            claim_payload.append(str(claim))
    return (
        f"VERIFICATION RUN: {run_id}\nSOURCE ID: {source_id}\nSOURCE VERSION: {source_version}\n"
        "CLAIMS JSON\n" + json.dumps(claim_payload, ensure_ascii=False, sort_keys=True) +
        "\nTRANSCRIPT START\n" + source_text + "\nTRANSCRIPT END"
    )
