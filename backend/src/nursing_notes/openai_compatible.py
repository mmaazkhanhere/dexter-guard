"""OpenAI-compatible model adapter for provider-agnostic generation."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import urlparse

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

    prompt_version = "nursing-note-openai-compatible-v2"
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
        self._uses_groq_json_mode = urlparse(self.base_url).hostname == "api.groq.com"
        self.client = client or OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def generate(self, source: Any, *, generation_run_id: str | None = None) -> GenerationResult:
        request: dict[str, Any] = {
            "model": self.model_id,
            "temperature": 0,
            "timeout": self.timeout_seconds,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(source)},
            ],
        }
        # Groq JSON Object Mode prevents prose, Markdown fences, and truncated
        # non-JSON preambles from reaching the schema boundary. Other
        # OpenAI-compatible providers retain the existing portable request.
        if self._uses_groq_json_mode:
            request["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**request)
        content = _response_content(response)
        payload = _materialize_source_anchors(_parse_json_object(content), source)
        payload["generationRunId"] = generation_run_id
        payload["modelId"] = self.model_id
        payload["promptVersion"] = self.prompt_version
        payload["schemaVersion"] = self.schema_version
        payload["rulesetVersion"] = self.ruleset_version
        return GenerationResult.model_validate(payload)


_SYSTEM_PROMPT = """You are an AI assistant that transforms synthetic German caregiver transcripts into professional nursing documentation.

Return only a valid JSON object. No Markdown or explanations.

OBJECTIVE:
Transform informal caregiver speech into concise, professional, natural German nursing documentation while preserving all facts.

GENERATION RULES:
1. Rewrite the transcript into professional nursing language.
2. Do not simply copy the transcript unless it is already written in appropriate documentation style.
3. Preserve all clinically relevant information, including measurements and units, times and temporal relationships, negations, uncertainty, resident-reported information, caregiver observations, actions, and assistance provided.
4. Never invent observations, diagnoses, treatments, medication details, or clinical conclusions.
5. Do not convert observations into medical diagnoses.
6. Do not remove important contextual information.
7. Do not invent resident identities or assignments.
8. Use neutral, factual German documentation language.

STRUCTURED FACTS:
Extract all relevant factual claims from the generated note. Each fact must include sourceQuote: an exact supporting substring from the original transcript. Do not calculate source offsets; the backend derives them deterministically from sourceQuote.

The JSON object must have this shape:
{
  "content": "German nursing note",
  "facts": [
    {
      "type": "OBSERVATION|SYMPTOM|MEASUREMENT|ACTION",
      "statement": "factual claim expressed in the generated note",
      "residentSubject": "the supplied resident ID",
      "sourceQuote": "exact excerpt from transcript",
      "polarity": "AFFIRMED|NEGATED",
      "certainty": "CERTAIN|UNCERTAIN",
      "attribution": "RESIDENT_REPORTED|CAREGIVER_OBSERVED or omit",
      "temporalQualifier": "exact source wording when applicable",
      "numericValue": "source value when applicable",
      "unit": "source unit when applicable",
      "provenance": "GENERATED_FROM_SOURCE"
    }
  ]
}

SOURCE EVIDENCE:
- Every factual claim must have supporting transcript evidence.
- sourceQuote must be an exact, non-empty substring of the original transcript.
- Never invent evidence or quotations.
- Preserve the complete temporal phrase when applicable. For example, if the transcript says "Bis 10:00 Uhr", the fact must use "Bis 10:00 Uhr" as temporalQualifier; do not omit "Bis" or reduce it to only "10:00 Uhr".
- If source evidence is insufficient, do not invent the fact.
- Ensure every factual statement in content is represented by the structured facts.
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


def _materialize_source_anchors(payload: dict[str, object], source: Any) -> dict[str, object]:
    """Replace model-supplied exact quotations with deterministic source spans.

    Character offsets are easy for an LLM to miscount, especially around German
    Unicode characters. The public nursing-fact contract still uses sourceAnchor,
    but the provider supplies sourceQuote and this adapter resolves it against the
    immutable transcript before Pydantic validation.
    """
    facts = payload.get("facts")
    if not isinstance(facts, list):
        return payload

    transcript = source.transcript_text
    materialized: list[object] = []
    for index, raw_fact in enumerate(facts):
        if not isinstance(raw_fact, Mapping):
            materialized.append(raw_fact)
            continue
        fact = dict(raw_fact)
        quote = fact.pop("sourceQuote", None)
        if quote is None:
            materialized.append(fact)
            continue
        if not isinstance(quote, str) or not quote:
            raise ValueError(f"facts[{index}].sourceQuote must be a non-empty string")
        start = transcript.find(quote)
        if start < 0:
            raise ValueError(f"facts[{index}].sourceQuote is not an exact transcript substring")
        if transcript.find(quote, start + 1) >= 0:
            raise ValueError(f"facts[{index}].sourceQuote is ambiguous in the transcript")
        fact["sourceAnchor"] = {
            "sourceId": source.source_id,
            "sourceVersion": source.source_version,
            "start": start,
            "end": start + len(quote),
        }
        materialized.append(fact)
    return {**payload, "facts": materialized}

