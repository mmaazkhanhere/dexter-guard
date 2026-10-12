"""Content-minimized coverage telemetry."""

from __future__ import annotations

from .contracts import CoverageRunFailed, CoverageRunSucceeded


def telemetry_for_run(run: CoverageRunSucceeded | CoverageRunFailed) -> dict[str, object]:
    """Return IDs, versions, counts, and safe metrics without transcript/note text."""
    payload: dict[str, object] = {
        "coverageRunId": run.coverage_run_id,
        "status": run.status.value,
        "sourceId": run.source_id,
        "sourceVersion": run.source_version,
        "noteId": run.note_id,
        "noteRevision": run.note_revision,
        "sourceFactExtractionRunId": run.source_fact_extraction_run_id,
        "claimSetId": run.claim_set_id,
        "rulesetVersion": run.ruleset_version,
        "datasetVersion": run.dataset_version,
        "providerVersion": run.provider_version,
        "modelVersion": run.model_version,
        "promptVersion": run.prompt_version,
        "correlationId": run.correlation_id,
        "idempotencyKey": run.idempotency_key,
        "executionMetrics": run.execution_metrics.model_dump(mode="json", by_alias=True),
    }
    if isinstance(run, CoverageRunSucceeded):
        payload["runtimeCounts"] = run.runtime_counts.model_dump(mode="json", by_alias=True)
        payload["linkedFindingCount"] = sum(len(item.related_finding_refs) for item in run.assessments)
    else:
        payload["failureCode"] = run.failure.code
    return payload
