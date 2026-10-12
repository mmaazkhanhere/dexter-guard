from tests.source_coverage.test_service import make_service
from source_coverage.observability import telemetry_for_run


def test_telemetry_is_content_minimized_and_contains_run_metrics():
    service, payload = make_service()
    run = service.execute(payload)
    telemetry = telemetry_for_run(run)
    assert telemetry["coverageRunId"] == run.coverage_run_id
    assert "transcriptText" not in telemetry and "noteText" not in telemetry
    assert "runtimeCounts" in telemetry
    assert "executionMetrics" in telemetry
