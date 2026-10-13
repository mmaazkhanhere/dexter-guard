import pytest

from human_review.ports import RetryingVerificationPorts, UpstreamRun


class TimeoutThenRunPorts:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def extract(self, note_id, revision):
        self.calls += 1
        if self.calls <= self.failures:
            raise TimeoutError("synthetic upstream timeout")
        return UpstreamRun("claims-1", "SUCCEEDED", "source-1", 1, note_id, revision, "claims-1")

    def evidence(self, note_id, revision, claim_set_id):
        return UpstreamRun("evidence-1", "SUCCEEDED", "source-1", 1, note_id, revision, claim_set_id)

    def validation(self, note_id, revision, claim_set_id):
        return UpstreamRun("validation-1", "SUCCEEDED", "source-1", 1, note_id, revision, claim_set_id)

    def coverage(self, note_id, revision, claim_set_id):
        return UpstreamRun("coverage-1", "SUCCEEDED", "source-1", 1, note_id, revision, claim_set_id)


def test_retrying_ports_retries_timeout_once_then_returns_the_single_upstream_result():
    delegate = TimeoutThenRunPorts(failures=1)
    retries: list[str] = []
    ports = RetryingVerificationPorts(delegate, max_attempts=2, on_retry=retries.append)

    run = ports.extract("note-1", 1)

    assert run.run_id == "claims-1"
    assert delegate.calls == 2
    assert retries == ["CLAIM_EXTRACTION"]


def test_retrying_ports_stops_after_its_bounded_attempt_limit():
    delegate = TimeoutThenRunPorts(failures=3)
    ports = RetryingVerificationPorts(delegate, max_attempts=2)

    with pytest.raises(TimeoutError, match="synthetic upstream timeout"):
        ports.extract("note-1", 1)

    assert delegate.calls == 2


def test_retrying_ports_rejects_an_invalid_attempt_limit():
    with pytest.raises(ValueError, match="positive"):
        RetryingVerificationPorts(TimeoutThenRunPorts(failures=0), max_attempts=0)
