from human_review.observability import InMemoryReviewLogger, ReviewMetrics


def test_review_metrics_track_terminal_statuses_and_replays_without_content():
    metrics = ReviewMetrics()
    metrics.record_verification(status="VALID", latency_ms=3.5)
    metrics.record_verification(status="INVALID", latency_ms=4.0, failure_code="PROVENANCE_CONFLICT")
    metrics.increment("retry_replays")
    snapshot = metrics.snapshot()
    assert snapshot.verification_attempts == 2
    assert snapshot.verification_successes == 1
    assert snapshot.verification_invalid == 1
    assert snapshot.retry_replays == 1
    assert snapshot.failure_codes == (("PROVENANCE_CONFLICT", 1),)


def test_review_logger_drops_content_bearing_fields():
    logger = InMemoryReviewLogger()
    logger.event("REVIEW_ACTION", note_text="sensitive", source_text="sensitive", reviewerLabel="reviewer", status="VALID")
    assert logger.events == [("REVIEW_ACTION", {"reviewerLabel": "reviewer", "status": "VALID"})]
