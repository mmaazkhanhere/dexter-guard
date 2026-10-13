# Frontend-to-Backend Traceability

| Frontend user action | Backend endpoint/contract | Request / response contract | Owning spec | Error states |
| --- | --- | --- | --- | --- |
| Submit transcript | POST /sources | CreateSourceRequest / SourceDocument | 001 | 400, 415 validation/type error |
| Retrieve source version | GET /sources/{id}/versions/{version} | path identity / SourceDocument | 001 | 404 |
| Select saved demonstration | GET /api/v1/saved-examples **proposed**, then source/evaluation retrieval | metadata / SavedExample | 009; 001/008 data | 503, 404 |
| Generate note and facts | POST /api/v1/notes/generate | GenerateRequest / NoteResponse | 002 | 400, 409, 422, 503, timeout |
| Import external note | POST /api/v1/notes/import | ImportRequest / NoteResponse | 002 | 400, 409, 422 |
| Retrieve note revision/facts | GET /api/v1/notes/{noteId}/revisions/{revision} **proposed** | immutable identity / note + structured facts | 002 | 404 |
| Extract claims (when not orchestrated) | POST /api/v1/claims/extract **proposed** | note revision reference / ExtractionResult | 003 | 404, 409, 503, failed terminal result |
| Verify claims | POST /api/v1/verification-runs | immutable references / VerificationRun | 004 | 400, 409, 503, typed failed run |
| Retrieve verification result | GET /api/v1/verification-runs/{runId} **proposed** | run identity / VerificationRun | 004 | 404 |
| Run deterministic validation | POST /api/v1/deterministic-validation-runs | references/alignment / ValidationRun | 005 | 404, 409, 422, 503 |
| Run source coverage | POST /api/v1/coverage-runs | immutable references / CoverageRun | 006 | 404, 409, 503 |
| Load review workspace | GET /api/v1/reviews/{noteId} | note/revision / ReviewContext | 007 | 404, 409, 503 |
| Save manual revision | POST /api/v1/reviews/{noteId}/revisions | expected revision/content/reviewer/idempotency / successor | 007 | 409 STALE_REVISION or FINAL_DISPOSITION_IMMUTABLE, 422 |
| List suggestions | GET /api/v1/reviews/{noteId}/suggestions | note/revision / suggestions | 007 | 404, 503 |
| Decide/adjudicate finding | POST .../findings/{findingId}/decisions | decision/rationale/reviewer/revision/idempotency / ReviewDecision | 007 | 400, 404, 409, 422 |
| Reverify claim feedback | POST .../findings/{findingId}/claim-reverification | claim/revision/reviewer/idempotency / feedback | 007 using 003/004 | 404, 409, 503 |
| Reverify complete note | POST /api/v1/reviews/{noteId}/full-verifications | revision/reviewer/idempotency / FullNoteVerification | 007 using 003–006 | 400, 404, 409, 422, 503, terminal failure |
| Approve | POST /api/v1/reviews/{noteId}/approve | current revision/full run/reviewer/idempotency / disposition | 007 | 409 APPROVAL_PRECONDITION_FAILED/STALE_REVISION |
| Reject | POST /api/v1/reviews/{noteId}/reject | current revision/reviewer/reason/idempotency / disposition | 007 | 404, 409, 422 |
| View history | GET /api/v1/reviews/{noteId}/audit | note identity / ordered events | 007 | 404, 503 |
| List saved evaluations | GET /api/v1/evaluation-runs | none / summaries | 008 | 503 |
| Run live evaluation/demo tracking | POST /api/v1/evaluation-runs | EvaluationRunRequest / EvaluationRun | 008 | 409, 422, 503, terminal failure |
| Inspect metrics/cases | GET /api/v1/evaluation-runs/{id} | run identity / EvaluationRun | 008 | 404 |
| Export evaluation | GET /api/v1/evaluation-runs/{id}/export | run identity / JSON export | 008 | 404 |
| Deployment health check | GET /api/v1/health **proposed** | none / safe Health | 009 | 503 |

Existing confirmations are based on current source modules/contracts. Routes marked **proposed** are required integration dependencies and must not be simulated in the browser.

