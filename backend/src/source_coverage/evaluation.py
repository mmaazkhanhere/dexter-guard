"""Metrics for manually annotated synthetic source-coverage cases."""

from __future__ import annotations

from collections.abc import Iterable


def evaluate_annotated_cases(cases: Iterable[dict[str, object]]) -> dict[str, object]:
    rows = list(cases)
    applicable = [row for row in rows if bool(row.get("applicable", True))]
    non_omissions = [row for row in applicable if row.get("expected") == "COVERED"]
    omissions = [row for row in applicable if row.get("expected") != "COVERED"]
    faithfully_covered = sum(1 for row in applicable if row.get("expected") == "COVERED" and row.get("observed") == "COVERED")
    correctly_flagged_omissions = sum(1 for row in omissions if row.get("observed") != "COVERED")
    false_warnings = sum(1 for row in non_omissions if row.get("observed") != "COVERED")
    return {
        "caseCount": len(rows),
        "applicableAnnotatedExpectedFacts": len(applicable),
        "faithfullyCoveredAnnotatedExpectedFacts": faithfully_covered,
        "benchmarkCompleteness": faithfully_covered / len(applicable) if applicable else None,
        "annotatedOmissions": len(omissions),
        "correctlyFlaggedAnnotatedOmissions": correctly_flagged_omissions,
        "omissionDetectionRecall": correctly_flagged_omissions / len(omissions) if omissions else None,
        "reviewedNonOmissions": len(non_omissions),
        "falseOmissionWarnings": false_warnings,
        "falseOmissionWarningRate": false_warnings / len(non_omissions) if non_omissions else None,
        "metricBasis": "MANUALLY_ANNOTATED_EXPECTED_FACTS",
    }
