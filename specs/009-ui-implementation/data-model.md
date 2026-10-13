# Frontend State and Shared Domain Models

Backend contracts are authoritative. The generated TypeScript client owns transport shapes; UI view models only add display/selection state and never create a parallel source of truth.

| Domain model | Backend owner | Frontend consumption |
| --- | --- | --- |
| SourceDocument | Spec 001 | sourceId, sourceVersion, residentTestId, language, immutable transcriptText, createdAt. |
| NursingNote / NoteRevision | Spec 002; revision lifecycle Spec 007 | note ID/revision, content, origin, source reference, status, predecessor metadata. |
| SourceFact | Spec 006 (and generated structured facts Spec 002) | fact category, atomic statement/attributes, expectation, source spans; facts are displayed, never calculated. |
| Claim | Spec 003 | ID, noteRevisionId, exact note span, text, semantic attributes, numeric values, extraction provenance. |
| EvidenceFinding | Spec 004 | claim ID, primary status, explanation, source spans/derived excerpts, discrepancies, policy/version provenance. |
| ValidationFinding | Spec 005 | rule/outcome, expected/observed value/unit, linked source fact/claim/evidence IDs, requiresReview; UI assigns no severity. |
| ReviewDecision | Spec 007 | immutable decision kind, rationale, reviewer label, finding/revision reference, timestamp. |
| VerificationRun | Specs 004, 006, 007 | immutable run ID, exact source/note/claim identities, terminal status, findings/failure, timestamps and metrics. |
| EvaluationCase | Spec 008 | case execution/scenario/candidate identity, results, stage runs, matches, failures, latency/cost. |
| EvaluationRun | Spec 008 | immutable run identity/origin/purpose/status, configuration, metric results, comparison, cases, failure summary. |

## Frontend-only models

**DocumentationWorkspaceState:** selectedExampleId, activeSourceIdentity, activeNoteIdentity, sourceForm status, generated/import draft mode, facts-panel selection. It stores IDs/revisions, never a mutable source record.

**SelectedFinding:** producer, stable finding ID, note ID/revision, source ID/version, claim ID/sourceFact ID, and span IDs. Selection becomes invalid when identity differs from current context.

**EvidenceHighlightSelection:** immutable text identity plus source spans and note spans returned by backend. Range conversion for rendering is derived-only and discarded when identity changes.

**UnsavedDraft:** baseNoteId, baseRevision, content, dirty, validation errors, save request ID. It cannot alter cached NursingNote until save returns a successor.

**VerificationRequestState:** operation, idempotencyKey, requested source/note/revision, startedAt, request token, phase (idle/pending/succeeded/failed/cancelled), retryable error. A terminal response is accepted only when requested identity equals current identity.

**ApprovalEligibilityPresentation:** server eligibility boolean/status, blocking findings, required fullVerificationId, explanation, freshness identity. It never locally calculates eligibility.

**EvaluationFilters:** selected run, scenario/tag/status/metric filters and display-only sort order. Filters do not recalculate metric values.

**ApiErrorState:** kind (validation/not-found/conflict/unavailable/timeout/malformed/network/unknown), stable code, safe message, field/path, correlation ID, retryable. It never marks an operation successful.

## Identity propagation

SourceDocument identity is (sourceId, sourceVersion). Every NoteRevision carries that immutable source identity; Claim carries noteRevisionId; evidence/validation/coverage/full verification runs bind source identity, note ID/revision, and upstream run IDs. Review decisions bind finding and revision. Query keys, mutation payloads, render guards, selection state, audit links, and approval UI must carry these fields.

Note revision changes invalidate current claim extraction/verification eligibility in the UI immediately, but server responses decide durable state. Historical runs retain their original identities and render read-only. An EvaluationRun never becomes a replacement for a live workflow record; its origin distinguishes historical saved results from newly executed runs.

