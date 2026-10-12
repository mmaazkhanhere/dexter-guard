"""Deterministic source-fact expectation and policy-key mapping."""

from .contracts import DocumentationExpectation, SourceFactCategory


def expectation_for(category: SourceFactCategory, *, explicit_uncertainty: bool = False) -> tuple[DocumentationExpectation, str | None]:
    if category is SourceFactCategory.MEASUREMENT:
        return DocumentationExpectation.REQUIRED, "MEASUREMENT_OMISSION"
    if category is SourceFactCategory.SYMPTOM:
        return DocumentationExpectation.IMPORTANT, "SYMPTOM_OMISSION"
    if category is SourceFactCategory.MOBILITY:
        return DocumentationExpectation.IMPORTANT, "MOBILITY_ASSISTANCE_OMISSION"
    if category is SourceFactCategory.CARE_ACTION:
        return DocumentationExpectation.IMPORTANT, "CARE_ACTION_OMISSION"
    if explicit_uncertainty:
        return DocumentationExpectation.IMPORTANT, "UNCERTAINTY_OMISSION"
    return DocumentationExpectation.CONTEXTUAL, None
