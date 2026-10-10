from claim_extraction.observability import InMemoryExtractionLogger


def test_observability_does_not_retain_note_or_claim_content() -> None:
    logger = InMemoryExtractionLogger()
    logger.event("completed", note_text="synthetic note", claim_text="synthetic claim", status="FAILED")
    assert logger.events == [("completed", {"status": "FAILED"})]
