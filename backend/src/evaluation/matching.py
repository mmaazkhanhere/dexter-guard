from __future__ import annotations

from collections.abc import Mapping, Sequence

from .contracts import FindingMatch, GroundTruthError, MatchDisposition, ObservedFinding, SourceSpan


def match_findings(
    findings: Sequence[ObservedFinding], errors: Sequence[GroundTruthError | Mapping[str, object]],
) -> tuple[FindingMatch, ...]:
    """Apply EVALUATION_MATCHING-v1 once, with deterministic one-to-one consumption."""
    normalized = tuple(error if isinstance(error, GroundTruthError) else GroundTruthError.model_validate(error) for error in errors)
    consumed: set[str] = set()
    output: list[FindingMatch] = []
    deferred: list[ObservedFinding] = []
    ordered = sorted(findings, key=lambda item: item.finding_key)

    # A coverage finding can sort ahead of a verifier finding for the same
    # target.  Consume exact matches first so output order never hides a fully
    # correct finding behind a weaker target-linked result.
    for finding in ordered:
        candidates = [error for error in normalized if error.error_id not in consumed and _target_matches(finding, error)]
        exact = [error for error in candidates if _fully_matches(finding, error)]
        if exact:
            error = sorted(exact, key=lambda item: (-_specificity(finding, item), item.error_id))[0]
            consumed.add(error.error_id)
            output.append(FindingMatch(errorId=error.error_id, findingKey=finding.finding_key, disposition=MatchDisposition.MATCHED, reasonCode="EXACT_TARGET_DISCREPANCY", specificityScore=_specificity(finding, error)))
        elif candidates:
            deferred.append(finding)
        elif any(_target_matches(finding, error) for error in normalized):
            output.append(FindingMatch(errorId="UNMATCHED", findingKey=finding.finding_key, disposition=MatchDisposition.DUPLICATE, reasonCode="TARGET_ALREADY_CONSUMED", specificityScore=1))
        elif finding.requires_correction_or_review:
            output.append(FindingMatch(errorId="UNMATCHED", findingKey=finding.finding_key, disposition=MatchDisposition.UNMATCHED_WARNING, reasonCode="NO_GROUND_TRUTH_TARGET", specificityScore=0))

    for finding in deferred:
        candidates = [error for error in normalized if error.error_id not in consumed and _target_matches(finding, error)]
        if candidates:
            error = sorted(candidates, key=lambda item: (-_specificity(finding, item), item.error_id))[0]
            consumed.add(error.error_id)
            output.append(FindingMatch(errorId=error.error_id, findingKey=finding.finding_key, disposition=MatchDisposition.TARGET_LINKED_MISCLASSIFICATION, reasonCode="TARGET_MATCH_BUT_DISCREPANCY_MISMATCH", specificityScore=_specificity(finding, error)))
        else:
            output.append(FindingMatch(errorId="UNMATCHED", findingKey=finding.finding_key, disposition=MatchDisposition.DUPLICATE, reasonCode="TARGET_ALREADY_CONSUMED", specificityScore=1))
    for error in normalized:
        if error.applicable and error.error_id not in consumed:
            output.append(FindingMatch(errorId=error.error_id, findingKey=None, disposition=MatchDisposition.FALSE_NEGATIVE, reasonCode="NO_VALID_FINDING", specificityScore=None))
    return tuple(output)


def _target_matches(finding: ObservedFinding, error: GroundTruthError) -> bool:
    return (
        (error.affected_annotated_claim_id is not None and finding.affected_claim_id == error.affected_annotated_claim_id)
        or (error.affected_source_fact_id is not None and finding.affected_source_fact_id == error.affected_source_fact_id)
    )


def _fully_matches(finding: ObservedFinding, error: GroundTruthError) -> bool:
    if error.expected_primary_status is not None and finding.primary_status_or_outcome != error.expected_primary_status.value:
        return False
    if error.required_discrepancy_or_rule is not None and finding.discrepancy_or_rule != error.required_discrepancy_or_rule:
        return False
    if error.conflicting_attribute is not None and error.conflicting_attribute not in (finding.conflicting_attribute_or_value or ""):
        return False
    if error.source_evidence_spans and not _same_spans(finding.source_spans, error.source_evidence_spans):
        return False
    return True


def _specificity(finding: ObservedFinding, error: GroundTruthError) -> int:
    return int(_target_matches(finding, error)) + int(_fully_matches(finding, error)) * 4 + int(bool(finding.source_spans and error.source_evidence_spans))


def _same_spans(left: Sequence[SourceSpan], right: Sequence[SourceSpan]) -> bool:
    return {(s.source_id, s.source_version, s.start, s.end) for s in left} == {(s.source_id, s.source_version, s.start, s.end) for s in right}

