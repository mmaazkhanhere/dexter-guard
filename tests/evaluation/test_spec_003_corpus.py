from tests.evaluation.fixtures.spec_003_corpus import (
    ANNOTATION_PROVENANCE,
    CORPUS_VERSION,
    DENOMINATOR_POLICY,
    SPEC_003_CORPUS,
)


def test_spec_003_corpus_is_versioned_and_has_required_release_metadata() -> None:
    assert CORPUS_VERSION == "spec-003-synthetic-v1"
    assert len(SPEC_003_CORPUS) >= 100
    assert len({case.case_id for case in SPEC_003_CORPUS}) == len(SPEC_003_CORPUS)
    assert {case.held_out for case in SPEC_003_CORPUS} == {False, True}
    assert all(case.annotation_provenance == ANNOTATION_PROVENANCE for case in SPEC_003_CORPUS)
    assert all(case.severity and case.materiality for case in SPEC_003_CORPUS)


def test_spec_003_corpus_contains_source_annotations_and_denominator_policy() -> None:
    assert all(case.source_reference["sourceTextHash"] for case in SPEC_003_CORPUS)
    assert all(case.source_annotation["sourceText"] == case.source_text for case in SPEC_003_CORPUS)
    assert all(case.evidence_data["evidenceText"] == case.source_text for case in SPEC_003_CORPUS)
    assert all(case.source_annotation["sourceSpan"]["endCodePointExclusive"] == len(case.source_text) for case in SPEC_003_CORPUS)
    assert set(DENOMINATOR_POLICY) >= {
        "claim_identification_precision",
        "claim_identification_recall",
        "claim_atomicity_correctness",
        "semantic_properties",
        "character_span_validity",
        "structured_output",
    }
