import time

import pytest

from source_coverage.matching import HeuristicGermanSemanticMatcher
from source_coverage.provider import BoundedSemanticMatcher, ProviderOutputError, ProviderTimeoutError
from tests.source_coverage.test_matching import claim, fact


def test_provider_output_is_validated_and_retry_count_is_bounded():
    calls = []

    def provider(facts, claims, run_id):
        calls.append(run_id)
        if len(calls) == 1:
            raise ValueError("transient provider failure")
        return HeuristicGermanSemanticMatcher().match(facts, claims, run_id=run_id)

    adapter = BoundedSemanticMatcher(provider, timeout_seconds=1)
    result = adapter.match([fact()], [claim("Bewohnerin berichtet über linksseitige Knieschmerzen.")], run_id="stable-run")
    assert result[0].kind.value == "FAITHFUL"
    assert calls == ["stable-run", "stable-run"]
    assert adapter.last_retry_count == 1


def test_malformed_provider_output_fails_closed():
    adapter = BoundedSemanticMatcher(lambda facts, claims, run_id: [{"status": "COVERED"}], timeout_seconds=1)
    with pytest.raises(ProviderOutputError):
        adapter.match([fact()], [claim("Bewohnerin berichtet über linksseitige Knieschmerzen.")], run_id="run-1")


def test_provider_timeout_is_not_uncertain_coverage():
    def slow(facts, claims, run_id):
        time.sleep(0.05)
        return ()

    adapter = BoundedSemanticMatcher(slow, timeout_seconds=0.001)
    with pytest.raises(ProviderTimeoutError):
        adapter.match([fact()], [], run_id="run-1")
