import pytest

from human_review.ports import ReferenceOnlyVerificationPorts, RetryingVerificationPorts, UpstreamRun


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


@pytest.mark.parametrize("operation", ["extract", "evidence", "validation", "coverage"])
def test_retrying_ports_bounds_timeout_retries_for_every_upstream_operation(operation):
    class FlakyPorts:
        def __init__(self):
            self.calls = {name: 0 for name in ("extract", "evidence", "validation", "coverage")}

        def _run(self, name, note_id, revision, claim_set_id="claims-1"):
            self.calls[name] += 1
            if self.calls[name] == 1:
                raise TimeoutError(name)
            return UpstreamRun(f"{name}-run", "SUCCEEDED", "source-1", 1, note_id, revision, claim_set_id)

        def extract(self, note_id, revision):
            return self._run("extract", note_id, revision)

        def evidence(self, note_id, revision, claim_set_id):
            return self._run("evidence", note_id, revision, claim_set_id)

        def validation(self, note_id, revision, claim_set_id):
            return self._run("validation", note_id, revision, claim_set_id)

        def coverage(self, note_id, revision, claim_set_id):
            return self._run("coverage", note_id, revision, claim_set_id)

    delegate = FlakyPorts()
    ports = RetryingVerificationPorts(delegate, max_attempts=2)
    if operation == "extract":
        result = ports.extract("note-1", 1)
    elif operation == "evidence":
        result = ports.evidence("note-1", 1, "claims-1")
    elif operation == "validation":
        result = ports.validation("note-1", 1, "claims-1")
    else:
        result = ports.coverage("note-1", 1, "claims-1")
    assert result.status == "SUCCEEDED"
    assert delegate.calls[operation] == 2


def test_retrying_ports_stops_after_its_bounded_attempt_limit():
    delegate = TimeoutThenRunPorts(failures=3)
    ports = RetryingVerificationPorts(delegate, max_attempts=2)

    with pytest.raises(TimeoutError, match="synthetic upstream timeout"):
        ports.extract("note-1", 1)

    assert delegate.calls == 2


def test_retrying_ports_rejects_an_invalid_attempt_limit():
    with pytest.raises(ValueError, match="positive"):
        RetryingVerificationPorts(TimeoutThenRunPorts(failures=0), max_attempts=0)


def test_reference_only_adapter_copies_terminal_metadata_and_discards_payload_content():
    class Upstream:
        def __init__(self, run_id):
            self.run_id = run_id
            self.status = "SUCCEEDED"
            self.source_id = "source-1"
            self.source_version = 1
            self.note_id = "note-1"
            self.note_revision = 1
            self.claim_set_id = "claims-1"
            self.transcript_text = "must not cross the boundary"

    adapter = ReferenceOnlyVerificationPorts(
        extract_claims=lambda note_id, revision: Upstream("claims-1"),
        verify_evidence=lambda note_id, revision, claim_set_id: Upstream("evidence-1"),
        validate_deterministically=lambda note_id, revision, claim_set_id: Upstream("validation-1"),
        read_coverage=lambda note_id, revision, claim_set_id: Upstream("coverage-1"),
    )
    run = adapter.extract("note-1", 1)
    assert run.run_id == "claims-1"
    assert not hasattr(run, "transcript_text")


def test_reference_only_adapter_rejects_malformed_upstream_metadata():
    with pytest.raises(ValueError, match="MALFORMED_UPSTREAM_RESULT"):
        ReferenceOnlyVerificationPorts(
            extract_claims=lambda *_: object(), verify_evidence=lambda *_: object(),
            validate_deterministically=lambda *_: object(), read_coverage=lambda *_: object(),
        ).extract("note-1", 1)
