from __future__ import annotations

from types import SimpleNamespace

from app.llm_config import evidence_verifier_from_environment
from evidence_verification.openai_compatible import OpenAICompatibleEvidenceVerifier


class FakeCompletions:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"findings": [{"claimId": "claim-1", "status": "SUPPORTED", "explanation": "ok", "sourceSpans": [], "discrepancies": []}]}'))],
            usage=SimpleNamespace(prompt_tokens=120, completion_tokens=30),
        )


def test_openai_compatible_verifier_captures_usage_and_cost() -> None:
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenAICompatibleEvidenceVerifier(
        api_key="secret",
        base_url="https://example.test/v1",
        model="verifier-model",
        input_cost_per_1k=0.01,
        output_cost_per_1k=0.02,
        client=client,
    )

    result = provider.verify(claims=(), source_text="Transcript", run_id="run-1", source_id="source-1", source_version=1)

    assert result["findings"][0]["claimId"] == "claim-1"
    assert provider.last_input_tokens == 120
    assert provider.last_output_tokens == 30
    assert provider.last_inference_cost == 0.0018
    assert completions.kwargs["model"] == "verifier-model"
    assert "Compare claim meaning, not wording" in completions.kwargs["messages"][0]["content"]
    assert completions.kwargs["max_tokens"] == 4096


def test_groq_verifier_uses_json_mode() -> None:
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenAICompatibleEvidenceVerifier(
        api_key="secret", base_url="https://api.groq.com/openai/v1", model="verifier-model", client=client,
    )

    provider.verify(claims=(), source_text="Transcript", run_id="run-1")

    assert completions.kwargs["response_format"] == {"type": "json_object"}


def test_verifier_configuration_is_optional_and_uses_verification_overrides() -> None:
    assert evidence_verifier_from_environment({}) is None
    provider = evidence_verifier_from_environment({
        "VERIFICATION_LLM_API_KEY": "secret",
        "VERIFICATION_LLM_MODEL": "verification-model",
        "VERIFICATION_LLM_BASE_URL": "https://example.test/v1",
        "LLM_TIMEOUT_SECONDS": "30",
        "VERIFICATION_LLM_INPUT_COST_PER_1K": "0.01",
        "VERIFICATION_LLM_OUTPUT_COST_PER_1K": "0.02",
    })

    assert isinstance(provider, OpenAICompatibleEvidenceVerifier)
    assert provider.model_id == "verification-model"
    assert provider.input_cost_per_1k == 0.01
    assert provider.output_cost_per_1k == 0.02
    assert provider.timeout_seconds == 45
    assert provider.max_output_tokens == 4096
