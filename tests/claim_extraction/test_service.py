from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

import pytest

from claim_extraction.models import ExtractionStatus
from claim_extraction.repository import InMemoryClaimRepository
from claim_extraction.service import ClaimExtractionService
from claim_extraction.spans import make_text_span


NOTE_ID = "note-1:r1"
NOTE = "Bewohnerin berichtet keine Schmerzen. Sie trank etwa 300 ml Wasser."


@dataclass(frozen=True)
class Context:
    note_revision_id: str = NOTE_ID
    note_body: str = NOTE
    note_body_hash: str = hashlib.sha256(NOTE.encode("utf-8")).hexdigest()
    resident_test_id: str = "resident-1"
    language: str = "de-DE"
    synthetic: bool = True
    source_reference: dict[str, object] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.source_reference is None:
            object.__setattr__(
                self,
                "source_reference",
                {
                    "sourceId": "source-1",
                    "sourceVersion": 1,
                    "sourceTextHash": "source-hash",
                    "normalizationPolicy": "unicode-code-point-v1",
                },
            )


class FakeReader:
    def __init__(self, context: Context | None = None):
        self.context = context or Context()

    def read(self, note_revision_id: str) -> Context:
        if note_revision_id != self.context.note_revision_id:
            raise KeyError(note_revision_id)
        return self.context


def provider_claim(note_id: str = NOTE_ID, resident: str = "resident-1") -> dict[str, object]:
    pain_start = NOTE.index("keine")
    water_start = NOTE.index("etwa")
    return {
        "id": "note-1:r1:c1",
        "noteRevisionId": note_id,
        "residentTestId": resident,
        "ordinal": 1,
        "category": "SYMPTOM",
        "statementSpan": make_text_span(NOTE, 0, NOTE.index(".")).model_dump(by_alias=True),
        "claimText": NOTE[:NOTE.index(".")],
        "polarity": "NEGATED",
        "negationCue": make_text_span(NOTE, pain_start, pain_start + 5).model_dump(by_alias=True),
        "certainty": "CERTAIN",
        "attribution": "CARE_RECIPIENT",
        "attributionText": "Bewohnerin berichtet",
        "attributionSpan": make_text_span(NOTE, 0, NOTE.index(" keine")).model_dump(by_alias=True),
        "numericValues": [],
        "extractionWarnings": [],
    }, {
        "id": "note-1:r1:c2",
        "noteRevisionId": note_id,
        "residentTestId": resident,
        "ordinal": 2,
        "category": "NUTRITION_HYDRATION",
        "statementSpan": make_text_span(NOTE, water_start, len(NOTE)).model_dump(by_alias=True),
        "claimText": NOTE[water_start:],
        "polarity": "AFFIRMED",
        "certainty": "CERTAIN",
        "attribution": "UNSPECIFIED",
        "numericValues": [{
            "raw": "etwa 300",
            "normalizedDecimal": "300",
            "unitRaw": "ml",
            "unitNormalized": "mL",
            "approximation": True,
            "valueSpan": make_text_span(NOTE, water_start, water_start + 8).model_dump(by_alias=True),
            "unitSpan": make_text_span(NOTE, water_start + 9, water_start + 11).model_dump(by_alias=True),
        }],
        "extractionWarnings": [],
    }


class FakeProvider:
    provider_version = "fake-provider-v1"
    model_version = "fake-model-v1"
    prompt_version = "claim-extraction-v1"

    def __init__(self, output: object | None = None, error: Exception | None = None):
        self.output = output if output is not None else {"claims": list(provider_claim())}
        self.error = error
        self.calls = 0

    def extract(self, note_text: str, **_: object) -> object:
        self.calls += 1
        if self.error:
            raise self.error
        return self.output


def service(provider: FakeProvider, reader: FakeReader | None = None) -> ClaimExtractionService:
    return ClaimExtractionService(
        reader or FakeReader(),
        provider,
        repository=InMemoryClaimRepository(),
        clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        id_factory=lambda: "fixed",
    )


def test_service_extracts_atomic_claims_and_persists_provenance() -> None:
    provider = FakeProvider()
    result = service(provider).extract_claims(NOTE_ID)

    assert result.status is ExtractionStatus.SUCCEEDED
    assert len(result.claims) == 2
    assert result.claims[0].polarity.value == "NEGATED"
    assert result.claims[0].attribution.value == "CARE_RECIPIENT"
    assert result.claims[1].numeric_values[0].raw == "etwa 300"
    assert result.claims[1].numeric_values[0].normalized_decimal == 300
    assert result.evidence_source_reference.source_id == "source-1"


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        {"claims": [{"bad": "schema"}]},
        {"claims": [provider_claim()[0], {"bad": "schema"}]},
    ],
)
def test_invalid_or_partially_valid_provider_output_fails_without_claims(output: object) -> None:
    result = service(FakeProvider(output=output)).extract_claims(NOTE_ID)
    assert result.status is ExtractionStatus.FAILED
    assert result.claims == ()
    assert result.error is not None


def test_changed_body_and_unknown_revision_fail_without_provider_call() -> None:
    provider = FakeProvider()
    extraction = service(provider)
    changed = extraction.extract_claims(NOTE_ID, note_body="changed")
    missing = extraction.extract_claims("note-404:r1")

    assert changed.status is ExtractionStatus.FAILED
    assert changed.error.code.value == "REVISION_MISMATCH"
    assert missing.status is ExtractionStatus.FAILED
    assert missing.error.code.value == "REVISION_NOT_FOUND"
    assert provider.calls == 0


def test_empty_output_uses_safeguard() -> None:
    empty = service(FakeProvider(output={"claims": []})).extract_claims(NOTE_ID)
    assert empty.status is ExtractionStatus.FAILED
    assert empty.error.code.value == "INTERNAL_VALIDATION_ERROR"

    no_assertion = Context(note_body="---", note_body_hash=hashlib.sha256(b"---").hexdigest())
    valid_empty = service(FakeProvider(output={"claims": []}), FakeReader(no_assertion)).extract_claims(NOTE_ID)
    assert valid_empty.status is ExtractionStatus.EMPTY
    assert valid_empty.claims == ()


def test_provider_timeout_is_typed_failure() -> None:
    provider = FakeProvider(error=TimeoutError())
    result = ClaimExtractionService(FakeReader(), provider, max_provider_attempts=2).extract_claims(NOTE_ID)
    assert result.status is ExtractionStatus.FAILED
    assert result.error.code.value == "PROVIDER_TIMEOUT"
    assert provider.calls == 2


def test_invalid_span_is_a_typed_failure_with_no_partial_claims() -> None:
    claims = list(provider_claim())
    claims[0] = dict(claims[0])
    claims[0]["statementSpan"] = dict(claims[0]["statementSpan"])
    claims[0]["statementSpan"]["text"] = "not the note"
    claims[0]["claimText"] = "not the note"
    result = service(FakeProvider(output={"claims": claims})).extract_claims(NOTE_ID)
    assert result.status is ExtractionStatus.FAILED
    assert result.error.code.value == "INVALID_SPAN"
    assert result.claims == ()


def test_current_result_is_revision_bound() -> None:
    provider = FakeProvider()
    repository = InMemoryClaimRepository()
    extraction = ClaimExtractionService(FakeReader(), provider, repository=repository, id_factory=lambda: "run")
    result = extraction.extract_claims(NOTE_ID)
    assert extraction.get_current_result(NOTE_ID) == result
    assert extraction.get_current_result("note-2:r1") is None
