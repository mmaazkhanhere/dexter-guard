"""Synthetic, labeled Spec 003 contribution cases.

These fixtures measure extraction structure and semantic preservation only; they do
not make clinical or evidence-support claims.
"""

SPEC_003_CASES = (
    {"id": "CLM-001", "text": "Bewohnerin ist wach.", "expected_claims": 1},
    {"id": "CLM-002", "text": "Bewohnerin ist wach. Sie isst Frühstück.", "expected_claims": 2},
    {"id": "CLM-003", "text": "Bewohnerin ist wach und orientiert.", "expected_claims": 2},
    {"id": "CLM-004", "text": "Kein Schmerz angegeben.", "expected_negation": True},
    {"id": "CLM-005", "text": "Möglicherweise leichte Übelkeit.", "expected_uncertainty": True},
    {"id": "CLM-006", "text": "Der Bewohner berichtet über Schwindel.", "expected_attribution": "CARE_RECIPIENT"},
    {"id": "CLM-007", "text": "Temperatur 37,8 °C.", "expected_numeric": "37,8"},
    {"id": "CLM-008", "text": "Temperatur 37,8 °C.", "expected_numeric": "37,8", "expected_normalized": "37.8"},
    {"id": "CLM-009", "text": "Hinweis auf Harnwegsinfekt.", "expected_category": "CLINICAL_CONCLUSION"},
    {"id": "CLM-010", "text": "Bewohnerin berichtet keine Schmerzen beim Transfer.", "expected_negation": True},
    {"id": "CLM-011", "text": "Bewohnerin ist wach.", "expected_revision_isolation": True},
    {"id": "CLM-012", "text": "synthetic malformed-output case", "expected_failure": "MALFORMED_PROVIDER_OUTPUT"},
    {"id": "CLM-013", "text": "---", "expected_empty": True},
    {"id": "CLM-013a", "text": "Bewohnerin ist wach.", "expected_failure": "INTERNAL_VALIDATION_ERROR"},
    {"id": "CLM-014", "text": "Metoprolol 25 mg oral verabreicht.", "expected_medication": True},
    {"id": "CLM-015", "text": "Bewohnerin ist wach.", "expected_failure": "NON_SYNTHETIC_INPUT"},
    {"id": "CLM-016", "text": "Bewohnerin ist wach.", "expected_failure": "PROVIDER_TIMEOUT"},
)
