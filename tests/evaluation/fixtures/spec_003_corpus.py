"""Versioned synthetic corpus metadata for the bounded Spec 003 evaluation.

The corpus is deliberately synthetic and evaluates extraction structure only. Its
source annotations are immutable note/source anchors; they are not evidence
support or clinical-severity judgments.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


CORPUS_VERSION = "spec-003-synthetic-v1"
ANNOTATION_PROVENANCE = "spec-003-template-annotation-v1"
HELD_OUT_POLICY = "Cases with index 097-120 are held out from prompt and rule tuning."
DENOMINATOR_POLICY = {
    "claim_identification_precision": "mean of per-case precision; zero predicted claims scores 1.0 when no claim is expected",
    "claim_identification_recall": "mean of per-case recall over all corpus cases",
    "claim_atomicity_correctness": "number of cases with expected claim count / total cases",
    "semantic_properties": "number of cases whose expected property matches / labeled cases for that property",
    "character_span_validity": "valid returned claim spans / returned claim spans; no returned claims scores 1.0",
    "structured_output": "successful or empty outcomes / total cases, and failed outcomes / total cases",
}


@dataclass(frozen=True)
class SyntheticSpec003Case:
    case_id: str
    source_text: str
    source_reference: dict[str, object]
    source_annotation: dict[str, object]
    evidence_data: dict[str, object]
    expected_claims: int
    labels: dict[str, object]
    severity: str
    materiality: str
    annotation_provenance: str
    held_out: bool


_TEMPLATES: tuple[tuple[str, int, dict[str, object]], ...] = (
    ("Bewohnerin ist wach.", 1, {}),
    ("Bewohner berichtet keine Schmerzen.", 1, {"expected_negation": True}),
    ("Vermutlich leichter Schwindel.", 1, {"expected_uncertainty": True}),
    ("Pflegekraft beobachtet Husten.", 1, {"expected_attribution": "CAREGIVER"}),
    ("Bewohnerin trank etwa 300 ml Wasser.", 1, {"expected_numeric": "etwa 300"}),
    ("Temperatur 37,8 °C.", 1, {"expected_numeric": "37,8", "expected_normalized": "37.8"}),
    ("Metoprolol 25 mg oral verabreicht.", 1, {"expected_medication": True}),
    ("Bewohnerin schläft seit zwei Stunden.", 1, {"expected_temporal": True}),
    ("Bewohnerin ist wach und orientiert.", 2, {}),
    ("Keine Übelkeit; Pflegekraft beobachtet Husten.", 2, {"expected_negation": True, "expected_attribution": "CAREGIVER"}),
    ("Vielleicht Schmerzen beim Transfer.", 1, {"expected_uncertainty": True}),
    ("---", 0, {"expected_empty": True}),
)


def _make_case(index: int) -> SyntheticSpec003Case:
    template_index = (index - 1) % len(_TEMPLATES)
    source_text, expected_claims, labels = _TEMPLATES[template_index]
    source_id = f"spec003-source-{index:03d}"
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    return SyntheticSpec003Case(
        case_id=f"CLM-{index:03d}",
        source_text=source_text,
        source_reference={
            "sourceId": source_id,
            "sourceVersion": 1,
            "sourceTextHash": source_hash,
            "normalizationPolicy": "unicode-code-point-v1",
        },
        source_annotation={
            "sourceText": source_text,
            "sourceSpan": {"startCodePoint": 0, "endCodePointExclusive": len(source_text)},
            "annotationType": "candidate-note-extraction",
        },
        evidence_data={
            "evidenceText": source_text,
            "evidenceSpan": {"startCodePoint": 0, "endCodePointExclusive": len(source_text)},
            "provenance": "synthetic-source-anchor",
        },
        expected_claims=expected_claims,
        labels={"caseId": f"CLM-{index:03d}", **labels},
        severity="NOT_ASSESSED_BY_SPEC_003",
        materiality="EXTRACTION_CONTRACT_ONLY",
        annotation_provenance=ANNOTATION_PROVENANCE,
        held_out=index >= 97,
    )


SPEC_003_CORPUS: tuple[SyntheticSpec003Case, ...] = tuple(_make_case(index) for index in range(1, 121))

