import json
from types import SimpleNamespace

import pytest

from app.llm_config import generation_adapter_from_environment
from app.main import create_app
from nursing_notes.adapters import OpenAICompatibleGenerationAdapter, UnavailableGenerationAdapter


class FakeCompletions:
    def __init__(self, content: object) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeClient:
    def __init__(self, content: object) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


def source() -> SimpleNamespace:
    return SimpleNamespace(
        source_id="source-1",
        source_version=1,
        resident_test_id="resident-1",
        transcript_text="Bewohner berichtet Schmerzen.",
    )


def payload() -> dict[str, object]:
    return {
        "content": "Pflegedokumentation: Bewohner berichtet Schmerzen.",
        "facts": [
            {
                "type": "SYMPTOM",
                "statement": "Schmerzen",
                "residentSubject": "resident-1",
                "sourceQuote": "Schmerzen",
                "polarity": "AFFIRMED",
                "certainty": "CERTAIN",
                "provenance": "GENERATED_FROM_SOURCE",
            }
        ],
    }


def test_openai_compatible_adapter_uses_common_chat_contract_and_metadata() -> None:
    client = FakeClient(json.dumps(payload()))
    adapter = OpenAICompatibleGenerationAdapter(
        api_key="secret",
        base_url="https://api.groq.com/openai/v1/",
        model="demo-model",
        client=client,
    )

    result = adapter.generate(source(), generation_run_id="generation-1")
    call = client.chat.completions.calls[0]

    assert result.model_id == "demo-model"
    assert result.generation_run_id == "generation-1"
    assert result.schema_version == "nursing-fact-v1"
    assert result.facts[0].source_anchor.start == 19
    assert result.facts[0].source_anchor.end == 28
    assert call["model"] == "demo-model"
    assert call["temperature"] == 0
    assert call["response_format"] == {"type": "json_object"}
    assert call["messages"][0]["role"] == "system"
    assert "source-1" in call["messages"][1]["content"]


@pytest.mark.parametrize("content", ["```json\n{}\n```", "[]", "not json"])
def test_openai_compatible_adapter_rejects_malformed_provider_payloads(content: str) -> None:
    adapter = OpenAICompatibleGenerationAdapter(
        api_key="secret",
        base_url="https://example.test/v1",
        model="demo-model",
        client=FakeClient(content),
    )

    with pytest.raises(ValueError):
        adapter.generate(source())


def test_openai_compatible_adapter_rejects_non_exact_or_ambiguous_source_quotes() -> None:
    invalid = payload()
    invalid["facts"][0]["sourceQuote"] = "nicht im Transkript"
    adapter = OpenAICompatibleGenerationAdapter(
        api_key="secret",
        base_url="https://api.groq.com/openai/v1",
        model="demo-model",
        client=FakeClient(json.dumps(invalid)),
    )

    with pytest.raises(ValueError, match="not an exact transcript substring"):
        adapter.generate(source())


def test_environment_factory_is_provider_agnostic_and_fails_closed_without_credentials() -> None:
    missing = generation_adapter_from_environment({})
    configured = generation_adapter_from_environment(
        {
            "LLM_API_KEY": "secret",
            "LLM_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "LLM_MODEL": "gemini-model",
            "LLM_TIMEOUT_SECONDS": "12",
        }
    )

    assert isinstance(missing, UnavailableGenerationAdapter)
    assert isinstance(configured, OpenAICompatibleGenerationAdapter)
    assert configured.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert configured.model_id == "gemini-model"
    assert configured.timeout_seconds == 12


def test_composed_app_wires_configured_adapter_without_exposing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_MODEL", "demo-model")

    app = create_app()

    assert isinstance(app.state.note_service.generation_adapter, OpenAICompatibleGenerationAdapter)
    assert not hasattr(app.state.note_service.generation_adapter, "api_key")

