"""OpenAI-compatible model adapter for provider-agnostic generation."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol

from openai import OpenAI

from .contracts import GenerationResult


class ChatCompletionsClient(Protocol):
    """Small seam used to test the adapter without network calls."""

    class _Completions(Protocol):
        def create(self, **kwargs: Any) -> Any: ...

    class _Chat(Protocol):
        completions: _Completions

    chat: _Chat


class OpenAICompatibleGenerationAdapter:
    """Generate structured nursing notes through any compatible chat endpoint.

    The adapter deliberately uses the common chat-completions surface instead of
    a provider SDK. Provider selection is configuration-only: API key, base URL,
    and model remain outside the application and are never sent to the browser.
    """

    prompt_version = "nursing-note-openai-compatible-v1"
    schema_version = "nursing-fact-v1"
    ruleset_version = "generation-guardrails-v1"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        client: ChatCompletionsClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must not be blank")
        if not base_url.strip():
            raise ValueError("base_url must not be blank")
        if not model.strip():
            raise ValueError("model must not be blank")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.model_id = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.client = client or OpenAI(api_key=api_key, base_url=self.base_url, timeout=timeout_seconds)

    def generate(self, source: Any, *, generation_run_id: str | None = None) -> GenerationResult:
        response = self.client.chat.completions.create(
            model=self.model_id,
            temperature=0,
            timeout=self.timeout_seconds,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(source)},
            ],
        )
        content = _response_content(response)
        payload = _parse_json_object(content)
        payload["generationRunId"] = generation_run_id
        payload["modelId"] = self.model_id
        payload["promptVersion"] = self.prompt_version
        payload["schemaVersion"] = self.schema_version
        payload["rulesetVersion"] = self.ruleset_version
        return GenerationResult.model_validate(payload)


_SYSTEM_PROMPT = """You generate professional German nursing documentation from one synthetic German transcript.
Return only one JSON object. Do not use Markdown fences or explanatory text.
The JSON object must have this shape:
{
  "content": "German nursing note",
  "facts": [
    {
      "type": "OBSERVATION|SYMPTOM|MEASUREMENT|ACTION",
      "statement": "exactly source-grounded German statement",
      "residentSubject": "the supplied resident ID",
      "sourceAnchor": {"sourceId": "the supplied source ID", "sourceVersion": 1, "start": 0, "end": 1},
      "polarity": "AFFIRMED|NEGATED",
      "certainty": "CERTAIN|UNCERTAIN",
      "attribution": "RESIDENT_REPORTED|CAREGIVER_OBSERVED or omit",
      "temporalQualifier": "source wording or omit",
      "numericValue": "source value or omit",
      "unit": "source unit or omit",
      "provenance": "GENERATED_FROM_SOURCE"
    }
  ]
}
Rules:
- Use only information explicitly present in the transcript.
- Preserve negation, uncertainty, attribution, time, measurements, and units.
- Use exact UTF-8 Python string character offsets for each sourceAnchor.
- Keep every sourceAnchor inside one source sentence and within the supplied transcript.
- Do not diagnose, recommend treatment, or add clinical conclusions.
- Every fact statement must be represented in content.
"""


def _user_prompt(source: Any) -> str:
    return (
        "SOURCE METADATA (do not change):\n"
        f"sourceId: {source.source_id}\n"
        f"sourceVersion: {source.source_version}\n"
        f"residentSubject: {source.resident_test_id}\n\n"
        "TRANSCRIPT START\n"
        f"{source.transcript_text}\n"
        "TRANSCRIPT END"
    )


def _response_content(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("provider response did not contain a choice")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            text = part.get("text") if isinstance(part, Mapping) else getattr(part, "text", None)
            if isinstance(text, str):
                text_parts.append(text)
        combined = "".join(text_parts).strip()
        if combined:
            return combined
    raise ValueError("provider response did not contain text content")


def _parse_json_object(content: str) -> dict[str, object]:
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("provider response was not valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("provider response must be a JSON object")
    return payload

