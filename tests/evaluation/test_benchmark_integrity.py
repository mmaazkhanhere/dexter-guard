from __future__ import annotations

import hashlib

import pytest

from evaluation.benchmark import default_dataset
from evaluation.dataset import DatasetValidationError, validate_dataset


def test_default_benchmark_is_accepted_and_covers_required_synthetic_scenarios() -> None:
    dataset = default_dataset()
    report = validate_dataset(dataset)
    assert report.accepted is True
    assert len(dataset.scenarios) >= 100
    assert {case.split.value for case in dataset.scenarios} == {"DEVELOPMENT", "VALIDATION", "HELD_OUT"}
    assert {tag for case in dataset.scenarios for tag in case.tags} >= {
        "SUPPORTED", "UNSUPPORTED_FACT", "EXPLICIT_CONTRADICTION", "NUMERIC_MISMATCH",
        "UNIT_MISMATCH", "NEGATION_CHANGE", "CERTAINTY_CHANGE", "ATTRIBUTION_CHANGE",
        "CLINICAL_INFERENCE", "IMPORTANT_OMISSION", "MULTIPLE_ERRORS", "AMBIGUOUS_SOURCE",
        "HARMLESS_PARAPHRASE",
    }


def test_validator_rejects_cross_split_family_and_duplicate_content() -> None:
    dataset = default_dataset()
    first = dataset.scenarios[0]
    changed = first.model_copy(update={"scenario_id": "leak", "split": "HELD_OUT"})
    with pytest.raises(DatasetValidationError, match="family|content"):
        validate_dataset(dataset.model_copy(update={"scenarios": (first, changed, *dataset.scenarios[2:])}))


def test_validator_rejects_source_span_hash_mismatch() -> None:
    dataset = default_dataset()
    case = dataset.scenarios[0]
    bad_source = case.source.model_copy(update={"source_text_hash": "0" * 64})
    with pytest.raises(DatasetValidationError, match="sourceTextHash"):
        validate_dataset(dataset.model_copy(update={"scenarios": (case.model_copy(update={"source": bad_source}), *dataset.scenarios[1:])}))


def test_dataset_content_hash_is_reproducible_and_does_not_include_runtime_output() -> None:
    dataset = default_dataset()
    assert dataset.content_hash == hashlib.sha256(dataset.canonical_content().encode()).hexdigest()
    assert "raw_output" not in dataset.canonical_content()

