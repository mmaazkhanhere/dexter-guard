from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .contracts import BenchmarkDataset, DatasetSplit, EvaluationCase
from .benchmark import CURATED_DATASET_ID, CURATED_DATASET_VERSION, CURATED_REQUIRED_TAGS


class DatasetValidationError(ValueError):
    """Raised when a benchmark cannot be safely scored."""


@dataclass(frozen=True)
class DatasetValidationReport:
    accepted: bool
    scenario_count: int
    selected_split: DatasetSplit | None = None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def validate_dataset(dataset: BenchmarkDataset, selected_split: DatasetSplit | None = None) -> DatasetValidationReport:
    if dataset.status.value != "ACCEPTED":
        raise DatasetValidationError("dataset status is not ACCEPTED")
    is_curated_companion = dataset.dataset_id == CURATED_DATASET_ID
    if is_curated_companion and dataset.dataset_version != CURATED_DATASET_VERSION:
        raise DatasetValidationError("curated companion dataset version is not recognised")
    minimum_scenarios = 30 if is_curated_companion else 100
    if len(dataset.scenarios) < minimum_scenarios or dataset.scenario_count != len(dataset.scenarios):
        raise DatasetValidationError(f"accepted dataset must contain at least {minimum_scenarios} scenarios")
    scenario_ids: set[str] = set()
    family_splits: dict[str, DatasetSplit] = {}
    source_hashes: dict[str, DatasetSplit] = {}
    candidate_hashes: dict[str, DatasetSplit] = {}
    required_tags = CURATED_REQUIRED_TAGS if is_curated_companion else {
        "SUPPORTED", "UNSUPPORTED_FACT", "EXPLICIT_CONTRADICTION", "NUMERIC_MISMATCH", "UNIT_MISMATCH",
        "NEGATION_CHANGE", "CERTAINTY_CHANGE", "ATTRIBUTION_CHANGE", "CLINICAL_INFERENCE",
        "IMPORTANT_OMISSION", "MULTIPLE_ERRORS", "AMBIGUOUS_SOURCE", "HARMLESS_PARAPHRASE",
    }
    observed_tags: set[str] = set()
    for case in dataset.scenarios:
        _validate_case(dataset, case)
        if case.scenario_id in scenario_ids:
            raise DatasetValidationError(f"duplicate scenario ID: {case.scenario_id}")
        scenario_ids.add(case.scenario_id)
        observed_tags.update(case.tags)
        prior_family = family_splits.get(case.scenario_family_id)
        if prior_family is not None and prior_family != case.split:
            raise DatasetValidationError(f"scenario family crosses splits: {case.scenario_family_id}")
        family_splits[case.scenario_family_id] = case.split
        if case.source.source_text_hash in source_hashes and source_hashes[case.source.source_text_hash] != case.split:
            raise DatasetValidationError("duplicate source content crosses splits")
        source_hashes[case.source.source_text_hash] = case.split
        for candidate in case.candidate_notes:
            if candidate.note_body_hash in candidate_hashes and candidate_hashes[candidate.note_body_hash] != case.split:
                raise DatasetValidationError("duplicate candidate content crosses splits")
            candidate_hashes[candidate.note_body_hash] = case.split
    missing = required_tags - observed_tags
    if missing:
        raise DatasetValidationError(f"required category coverage missing: {sorted(missing)}")
    if dataset.content_hash != _digest(dataset.canonical_content()):
        raise DatasetValidationError("dataset contentHash does not match canonical content")
    if is_curated_companion and any(case.split is not DatasetSplit.HELD_OUT for case in dataset.scenarios):
        raise DatasetValidationError("curated companion cases must remain held out")
    if selected_split is not None and not any(case.split is selected_split for case in dataset.scenarios):
        raise DatasetValidationError("selected split has no cases")
    return DatasetValidationReport(True, len(dataset.scenarios), selected_split)


def _validate_case(dataset: BenchmarkDataset, case: EvaluationCase) -> None:
    if case.dataset_version != dataset.dataset_version:
        raise DatasetValidationError(f"case {case.scenario_id} has mismatched datasetVersion")
    if _digest(case.source.transcript_text) != case.source.source_text_hash:
        raise DatasetValidationError(f"sourceTextHash mismatch for {case.scenario_id}")
    for fact in case.reference_facts:
        for span in fact.source_spans:
            _validate_span(span, case.source.source_id, case.source.source_version, case.source.transcript_text)
    for candidate in case.candidate_notes:
        if _digest(candidate.note_body) != candidate.note_body_hash:
            raise DatasetValidationError(f"noteBodyHash mismatch for {candidate.candidate_id}")
        claim_ids = {claim.annotated_claim_id for claim in candidate.annotated_claims}
        fact_ids = {fact.source_fact_id for fact in case.reference_facts}
        for error in candidate.error_instances:
            if error.candidate_id != candidate.candidate_id or (error.affected_annotated_claim_id not in claim_ids if error.affected_annotated_claim_id else error.affected_source_fact_id not in fact_ids):
                raise DatasetValidationError(f"invalid error target in {error.error_id}")
            for span in error.source_evidence_spans:
                _validate_span(span, case.source.source_id, case.source.source_version, case.source.transcript_text)
        for claim in candidate.annotated_claims:
            for span in claim.expected_evidence_spans:
                _validate_span(span, case.source.source_id, case.source.source_version, case.source.transcript_text)


def _validate_span(span, source_id: str, source_version: int, source_text: str) -> None:
    if (span.source_id, span.source_version) != (source_id, source_version) or span.end > len(source_text):
        raise DatasetValidationError("source span does not match immutable source version")

