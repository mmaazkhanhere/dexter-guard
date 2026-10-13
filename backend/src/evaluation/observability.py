from __future__ import annotations

from threading import Lock


_FORBIDDEN = {"source_text", "transcript", "note_body", "note", "prompt", "prompt_body", "raw_output", "claim_text", "content", "credentials"}


class EvaluationTelemetry:
    """Content-minimised structured telemetry for evaluation runs."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self._lock = Lock()

    def record(self, event_name: str, **metadata: object) -> None:
        safe = {key: value for key, value in metadata.items() if key.lower() not in _FORBIDDEN}
        safe["event"] = event_name
        with self._lock:
            self.events.append(safe)


def safe_configuration(**metadata: object) -> dict[str, object]:
    return {key: value for key, value in metadata.items() if key.lower() not in _FORBIDDEN}

