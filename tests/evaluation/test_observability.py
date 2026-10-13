from evaluation.observability import EvaluationTelemetry, safe_configuration


def test_telemetry_excludes_source_note_prompt_and_raw_provider_content() -> None:
    telemetry = EvaluationTelemetry()
    telemetry.record("case", source_text="synthetic text", note_body="note", prompt="prompt", raw_output="raw", duration_ms=12, failure_code="TIMEOUT")
    event = telemetry.events[0]
    assert "source_text" not in event and "note_body" not in event and "prompt" not in event and "raw_output" not in event
    assert event["duration_ms"] == 12
    config = safe_configuration(code_version="abc", model_id="model", prompt_body="do not retain", input_tokens=10, estimated_cost=0.01)
    assert "prompt_body" not in config
    assert config["input_tokens"] == 10

