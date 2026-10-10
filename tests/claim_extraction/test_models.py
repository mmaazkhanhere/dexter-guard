from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from pydantic import TypeAdapter

from claim_extraction.models import (
    Attribution,
    Certainty,
    Claim,
    ClaimCategory,
    EvidenceSourceReference,
    ExtractionEmpty,
    ExtractionFailed,
    ExtractionErrorCode,
    ExtractionResult,
    ExtractionSucceeded,
    NumericValue,
    Polarity,
    TextSpan,
)


def span(text: str, start: int, end: int) -> TextSpan:
    return TextSpan(
        startCodePoint=start,
        endCodePointExclusive=end,
        startUtf16=start,
        endUtf16Exclusive=end,
        text=text[start:end],
    )


def reference() -> EvidenceSourceReference:
    return EvidenceSourceReference(
        sourceId="source-1",
        sourceVersion=1,
        sourceTextHash="a" * 64,
        normalizationPolicy="unicode-code-point-v1",
    )


def claim() -> Claim:
    text = "Keine Schmerzen"
    return Claim(
        id="note-1:r1:c1",
        noteRevisionId="note-1:r1",
        residentTestId="resident-1",
        ordinal=1,
        category=ClaimCategory.SYMPTOM,
        statementSpan=span(text, 0, len(text)),
        claimText=text,
        polarity=Polarity.NEGATED,
        negationCue=span(text, 0, 5),
        certainty=Certainty.CERTAIN,
        attribution=Attribution.UNSPECIFIED,
        numericValues=(),
        extractionWarnings=(),
    )


def test_claim_contract_preserves_aliases_and_semantic_fields() -> None:
    result = ExtractionSucceeded(
        extractionRunId="run-1",
        noteRevisionId="note-1:r1",
        noteBodyHash="b" * 64,
        evidenceSourceReference=reference(),
        extractorVersion="claim-extractor-v1",
        providerVersion="fake-v1",
        modelVersion="fake-model",
        promptVersion="claim-extraction-v1",
        outputSchemaVersion="claim-extraction-v1",
        claims=(claim(),),
        extractedAt=datetime.now(timezone.utc),
    )

    payload = result.model_dump(mode="json", by_alias=True)

    assert payload["status"] == "SUCCEEDED"
    assert payload["noteRevisionId"] == "note-1:r1"
    assert payload["claims"][0]["polarity"] == "NEGATED"
    assert payload["claims"][0]["negationCue"]["text"] == "Keine"


def test_numeric_decimal_comma_serializes_as_decimal_string() -> None:
    value = NumericValue(
        raw="ca. 37,8",
        normalizedDecimal=Decimal("37.8"),
        unitRaw="°C",
        unitNormalized="C",
        approximation=True,
        valueSpan=span("ca. 37,8", 0, 8),
        unitSpan=TextSpan(
            startCodePoint=0,
            endCodePointExclusive=2,
            startUtf16=0,
            endUtf16Exclusive=2,
            text="°C",
        ),
    )

    payload = value.model_dump(mode="json", by_alias=True)
    assert payload["normalizedDecimal"] == "37.8"
    assert payload["raw"] == "ca. 37,8"


def test_claim_rejects_mismatched_claim_text_and_span() -> None:
    with pytest.raises(ValidationError):
        Claim(
            id="c1",
            noteRevisionId="note-1:r1",
            residentTestId="resident-1",
            ordinal=1,
            category="OBSERVATION",
            statementSpan=span("wach", 0, 4),
            claimText="orientiert",
            polarity="AFFIRMED",
            certainty="CERTAIN",
            attribution="UNSPECIFIED",
            numericValues=(),
            extractionWarnings=(),
        )


def test_negated_claim_requires_a_direct_negation_cue() -> None:
    with pytest.raises(ValidationError):
        Claim(
            id="c1",
            noteRevisionId="note-1:r1",
            residentTestId="resident-1",
            ordinal=1,
            category="SYMPTOM",
            statementSpan=span("keine Schmerzen", 0, 14),
            claimText="keine Schmerzen",
            polarity="NEGATED",
            certainty="CERTAIN",
            attribution="UNSPECIFIED",
            numericValues=(),
            extractionWarnings=(),
        )


def test_discriminated_result_forbids_error_on_success_and_claims_on_failure() -> None:
    result = TypeAdapter(ExtractionResult).validate_python(
        {
            "status": "FAILED",
            "extractionRunId": "run-1",
            "extractorVersion": "v1",
            "outputSchemaVersion": "v1",
            "claims": [],
            "error": {
                "code": "INVALID_SPAN",
                "message": "The provider span does not match the note.",
                "retryable": False,
            },
            "extractedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    assert isinstance(result, ExtractionFailed)
    assert result.error.code is ExtractionErrorCode.INVALID_SPAN

    with pytest.raises(ValidationError):
        TypeAdapter(ExtractionResult).validate_python(
            {
                "status": "FAILED",
                "extractionRunId": "run-1",
                "extractorVersion": "v1",
                "outputSchemaVersion": "v1",
                "claims": [claim().model_dump(by_alias=True)],
                "error": {"code": "INVALID_SPAN", "message": "bad", "retryable": False},
                "extractedAt": datetime.now(timezone.utc).isoformat(),
            }
        )

    with pytest.raises(ValidationError):
        TypeAdapter(ExtractionResult).validate_python(
            {
                "status": "EMPTY",
                "extractionRunId": "run-1",
                "noteRevisionId": "note-1:r1",
                "noteBodyHash": "b" * 64,
                "evidenceSourceReference": reference().model_dump(by_alias=True),
                "extractorVersion": "v1",
                "outputSchemaVersion": "v1",
                "claims": [],
                "error": {"code": "INVALID_SPAN", "message": "bad", "retryable": False},
                "extractedAt": datetime.now(timezone.utc).isoformat(),
            }
        )


def test_empty_result_is_typed_and_has_no_claims() -> None:
    result = ExtractionEmpty(
        extractionRunId="run-1",
        noteRevisionId="note-1:r1",
        noteBodyHash="b" * 64,
        evidenceSourceReference=reference(),
        extractorVersion="v1",
        outputSchemaVersion="v1",
        claims=(),
        extractedAt=datetime.now(timezone.utc),
    )
    assert result.status == "EMPTY"
    assert result.claims == ()
