# Spec 006 Requirement-to-Test Traceability

| Requirement/scenario | Executable evidence |
| --- | --- |
| FR-14.1 source facts and spans | `tests/source_coverage/test_extraction.py`; `test_acceptance.py::test_cov_001`–`test_cov_009` |
| FR-14.2 negation, certainty, attribution, temporality, laterality, measurements | `test_extraction.py`; `test_matching.py`; COV-003–COV-006 |
| FR-14.3 semantic comparison | `test_matching.py`; COV-001, COV-003, COV-004, COV-006, COV-010, COV-011 |
| FR-14.4 five statuses and precedence | `contracts.py` validators; `test_matching.py`; COV-002, COV-003, COV-005, COV-006, COV-009, COV-011 |
| FR-14.5 evidence-linked findings and review boundary | `test_acceptance.py::test_cov_002`, `test_cov_005`, `test_cov_007`, `test_cov_009`; `test_api.py` |
| FR-14.6 Spec 004/005 correlation | `test_acceptance.py::test_cov_010`; `test_service.py` related-finding repository boundary |
| FR-14.7 source/note revision integrity | `test_service.py::test_cross_revision_claim_set_is_rejected_and_new_revision_creates_new_run`; COV-008 |
| FR-14.8 benchmark metrics | `test_acceptance.py::test_evaluation_metrics_use_manual_annotations_and_report_raw_counts`; versioned evaluation JSON |
| COV-001–COV-010 | `tests/source_coverage/test_acceptance.py::test_cov_001` through `test_cov_010` |
| COV-011 regression | `tests/source_coverage/test_acceptance.py::test_cov_011_faithful_duplicate_precedes_distorted_duplicate` |
| Contract/error/telemetry gates | `test_contracts.py`, `test_provider.py`, `test_api.py`, `test_observability.py` |

All tests use synthetic German data. No test supplies transcript prose or a
desired status through the public run request.
