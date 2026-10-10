# Feature 001 traceability

| Requirement / invariant | Acceptance tests | Implementation boundary |
| --- | --- | --- |
| FR-01, AC-001, AC-004, AC-011 | `test_source_submission.py` valid, resident, audio/multi-value cases | `contracts.py`, `validation.py`, `app.py` |
| AC-002, FR-02 | blank, malformed, non-text, unsupported, and no-partial-persistence tests | `validation.py`, `app.py` |
| AC-003, AC-005 | unique-ID and exact round-trip tests | `service.py`, `repository.py` |
| AC-006, AC-009, FR-05, FR-06 | historical retrieval, stale, and concurrent revision tests | `repository.py`, `service.py` |
| AC-007, AC-008, FR-08 | Unicode, combining-mark, CRLF, boundary, and missing-reference tests | `spans.py`, `service.py` |
| AC-010, AC-012, FR-09 | Pydantic/OpenAPI contract and no-LLM tests | `contracts.py`, `contracts/source-api.yaml` |

All tests use deterministic in-memory persistence and do not call a model provider or network service.
