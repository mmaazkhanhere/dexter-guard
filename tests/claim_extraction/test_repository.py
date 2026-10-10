from datetime import datetime, timezone

from claim_extraction.models import ExtractionError, ExtractionFailed, ExtractionSucceeded
from claim_extraction.repository import InMemoryClaimRepository, SQLiteClaimRepository
from claim_extraction.spans import make_text_span
from claim_extraction.models import Claim


def result(run_id: str, status: str = "SUCCEEDED"):
    note = "Bewohnerin ist wach."
    claim = Claim(
        id=f"{run_id}:c1",
        noteRevisionId="note-1:r1",
        residentTestId="resident-1",
        ordinal=1,
        category="OBSERVATION",
        statementSpan=make_text_span(note, 0, len(note) - 1),
        claimText=note[:-1],
        polarity="AFFIRMED",
        certainty="CERTAIN",
        attribution="UNSPECIFIED",
        numericValues=(),
        extractionWarnings=(),
    )
    common = {
        "extractionRunId": run_id,
        "extractorVersion": "v1",
        "outputSchemaVersion": "v1",
        "claims": (claim,),
        "extractedAt": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "noteRevisionId": "note-1:r1",
        "noteBodyHash": "b" * 64,
        "evidenceSourceReference": {
            "sourceId": "source-1",
            "sourceVersion": 1,
            "sourceTextHash": "s" * 64,
            "normalizationPolicy": "unicode-code-point-v1",
        },
    }
    if status == "SUCCEEDED":
        return ExtractionSucceeded(**common)
    return ExtractionFailed(
        extractionRunId=run_id,
        extractorVersion="v1",
        outputSchemaVersion="v1",
        claims=(),
        extractedAt=common["extractedAt"],
        error=ExtractionError(code="INVALID_SCHEMA", message="invalid", retryable=False),
    )


def test_in_memory_repository_is_append_only_and_current_is_revision_bound() -> None:
    repository = InMemoryClaimRepository()
    first = result("run-1")
    second = result("run-2")
    repository.save(first)
    repository.save(second)
    assert repository.get_current_result("note-1:r1") == second
    assert repository.get_current_result("note-404:r1") is None
    repository.save(result("run-failed", "FAILED"))
    assert repository.get_current_result("note-1:r1") == second


def test_sqlite_repository_round_trips_results_and_does_not_persist_failed_claims(tmp_path) -> None:
    repository = SQLiteClaimRepository(tmp_path / "claims.sqlite3")
    repository.save(result("run-1"))
    repository.save(result("run-failed", "FAILED"))
    assert repository.get_current_result("note-1:r1").claims[0].claim_text == "Bewohnerin ist wach"
    assert repository.run_count() == 2
    assert repository.claim_count() == 1
    repository.close()
