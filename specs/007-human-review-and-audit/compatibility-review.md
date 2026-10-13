# Spec 007 Compatibility Review

**Evidence status:** T001 and T002 evidence is complete for the current repository snapshot.
This record is an implementation compatibility inspection, not independent requirements-quality
approval and not approval of a future production transport between specifications.

**Review date:** 2026-10-13
**Reviewed repository:** `dexter-guard` working tree before this documentation update
**Evidence policy:** synthetic identifiers and metadata only; no source transcript or patient data
is copied into this report.

**Status:** T001-T002 repository-inspection and contract-evidence work is complete. The
independent requirements-quality checklist remains reviewer-owned and is not self-approved here.

The concrete repository was inspected on 2026-10-13. Existing implementations are local
Python modules with frozen Pydantic contracts, in-memory repositories, SQLite note/source
repositories, and FastAPI adapters. Spec 007 uses injected ports for the missing aggregate
boundary rather than inventing upstream HTTP endpoints.

For each upstream specification, the compatibility record must include:

- actual module/service owner and callable interface;
- contract and schema version identifiers;
- immutable source, note-revision, claim-set, run, and error-envelope identities;
- terminal status, timeout, bounded-retry, and idempotency behavior;
- repository transaction/migration constraints and test fixtures;
- exact adapter evidence used by the Spec 007 integration tests.

The required Spec 007 ports are reference-only adapters:

| Upstream | Required adapter output | Fail-closed condition |
| --- | --- | --- |
| Spec 001 | Immutable source/version and validated code-point spans | Missing source, version mismatch, or invalid offsets |
| Spec 002 | Immutable note revision and source binding | Mutable/in-place note or stale revision |
| Spec 003 | Current claim set for the exact note revision | Missing/empty/unbound claim set |
| Spec 004 | Terminal evidence run and findings | Unavailable, malformed, or mismatched run |
| Spec 005 | Terminal deterministic-validation run | Missing source facts/alignment or unavailable adapter |
| Spec 006 | Terminal coverage run and unresolved-item state | Malformed run or unresolved source item |

This report records implementation compatibility evidence; it does not claim production
integration approval or waive the independent requirements-quality gate.

## Inspected implementation evidence

| Upstream | Actual owner/interface | Verified contract and behavior | Remaining gap |
| --- | --- | --- | --- |
| Spec 001 | `source_ingestion.contracts.SourceDocument`, `SourceSpan`; `SourceRepository.get`; `SourceIngestionService.resolve_span` | Immutable `(source_id, source_version)` identity, zero-based end-exclusive code-point spans, structured source errors | Spec 007 needs an injected source reader for review display; no review-specific endpoint is assumed. |
| Spec 002 | `nursing_notes.contracts.NoteRevisionRecord`; `NoteRepository.get/create`; `InMemoryNoteRepository` and `SQLiteNoteRepository` | Append-only revisions, predecessor check, source binding, `NOTE_VERSION_CONFLICT` | Spec 007 successor creation must use a compatible boundary; current local service slice stores a review projection and does not mutate upstream rows. |
| Spec 003 | `claim_extraction.models.ExtractionResult`; `ClaimExtractionService.extract_claims/get_current_result`; `ClaimRepository` | `SUCCEEDED`, `EMPTY`, `FAILED`; exact note revision/body/source references; bounded provider timeout/retry in service | No review-facing facade; Spec 007 `ClaimExtractionPort` is injected and reference-only. |
| Spec 004 | `evidence_verification.contracts.VerificationRun`; `VerificationService.verify`; repository | Terminal succeeded/failed statuses, exact source/note/claim-set binding, idempotency and provider failure outcomes | No atomic full-note aggregate across 004/005/006; Spec 007 composes ports. |
| Spec 005 | `deterministic_validation.contracts.ValidationRun`; `DeterministicValidationService.execute` | Immutable source/note references and explicit source-fact/claim/alignment IDs; unavailable alignment is typed | No public `run_for_revision` adapter; Spec 007 port remains dependency-injected and must not create alignments. |
| Spec 006 | `source_coverage.contracts.CoverageRun`; `SourceCoverageService.execute` | Terminal success/failure, exact source/note/claim-set identity, unresolved source-item count and policy keys | Raw suggestions remain display-only; unresolved source items remain approval-blocking. |

Timeout/retry behavior remains owned by each upstream service. Spec 007 treats unavailable,
malformed, failed, or mismatched adapter output as non-approval evidence. No migration
dependency is introduced; review SQLite schema initialization is local and idempotent.

## Repository conventions and actual route inventory (T001)

The inspected repository uses Python 3.11 `src/<component>` packages, Pydantic v2 models with
`frozen=True` and `extra="forbid"`, FastAPI `create_app` factories, `Protocol` repository
boundaries, injected in-memory doubles, and SQLite `CREATE TABLE IF NOT EXISTS` initialization.
SQLite writers use `RLock` and `BEGIN IMMEDIATE`; there is no migration framework. `pyproject.toml`
configures pytest with `tests` as the root and `-q`; API tests use FastAPI `TestClient`, while
service tests inject deterministic fakes. The established validation workflow is pytest,
`python -m compileall`, and `git diff --check`.

| Specification | Actual owner/interface | Route/status when configured | Availability behavior |
| --- | --- | --- | --- |
| 001 | `SourceIngestionService`; `source_ingestion.app:create_app` | `POST /sources` (201), `POST /sources/{source_id}/versions` (201), `GET /sources/{source_id}/versions/{source_version}` (200), `POST /source-spans/resolve` (200) | `SourceError` is handled by the shared app. |
| 002 | `NursingNoteService`; shared app | `POST /api/v1/notes/generate` (201), `POST /api/v1/notes/import` (201) | Provider failures are typed `NoteError` responses. |
| 003 | `ClaimExtractionService.extract_claims/get_current_result`; `ClaimRepository` | No HTTP route exists | Spec 007 injects an in-process/reference-only adapter; no endpoint is invented. |
| 004 | `VerificationService.verify`; shared app | `POST /api/v1/verification-runs` (200) | Missing service returns 503 `VERIFIER_UNAVAILABLE`; terminal failures are `VerificationRunFailed`. |
| 005 | `DeterministicValidationService.execute`; shared app | `POST /api/v1/deterministic-validation-runs` (200) | Missing service returns 503 `DEPENDENCY_UNAVAILABLE`; typed schema/provenance errors remain owned by Spec 005. |
| 006 | `SourceCoverageService.execute`; `source_coverage.api:create_app` and shared app | `POST /api/v1/coverage-runs` (200) | Missing service returns 503 `DEPENDENCY_UNAVAILABLE`; typed schema/provenance/provider errors are preserved. |

## Contract, identity, and error-envelope validation (T002)

The following values were checked against the actual Pydantic models and service code. Every
adapter input is an immutable reference or structured run record; Spec 007 never treats request
prose, candidate-note content, or client claim text as evidence authority.

| Upstream | Actual identity/version contract | Terminal/error behavior | Spec 007 rule |
| --- | --- | --- | --- |
| 001 | `SourceDocument.source_id/source_version/resident_test_id/language`; `SourceSpan` uses zero-based, start-inclusive/end-exclusive code-point offsets. | `ErrorCode` includes `SOURCE_NOT_FOUND`, `SOURCE_VERSION_NOT_FOUND`, `VERSION_CONFLICT`, and `INVALID_SOURCE_SPAN`. | Accept only immutable source/version and validated spans; missing or invalid spans are unavailable evidence. |
| 002 | `NoteRevisionRecord.note_id/revision`, predecessor ID, source binding, `source_text_hash`, and `normalization_policy`; append-only `NoteRepository`. | `NoteErrorCode` includes `NOTE_NOT_FOUND` and `NOTE_VERSION_CONFLICT`. | Bind every review entity to exact note/revision; never overwrite an upstream row. |
| 003 | `ExtractionResult.extraction_run_id`; successful/empty records carry `note_revision_id`, `note_body_hash`, `validation_run_id`, and `EvidenceSourceReference`; claims carry stable IDs and `noteRevisionId`. | `SUCCEEDED`, `EMPTY`, `FAILED`; failures include revision mismatch, timeout, and unavailable-provider codes. | Inject `get_current_result`/extraction behavior as a reference-only port; failed/empty sets cannot authorize approval. |
| 004 | `VerificationRun` binds run ID, source/version, note/revision, claim set, idempotency key; policy versions are `EVIDENCE_STATUS-v1` and `EVIDENCE_ANNOTATION-v1`. | `SUCCEEDED` or `FAILED_VALIDATION`, `FAILED_EVIDENCE_INTEGRITY`, `FAILED_VERIFIER`, `FAILED_PERSISTENCE`; timeout/unavailable/malformed output is terminal failure. | Require exact provenance and terminal success for approval; preserve failures for audit. |
| 005 | `ValidationRun` binds run ID, source/version, note/revision, input digest, `DVE-CONTRACT-v1`, `DVE-RULESET-v1`, and explicit fact/claim/alignment IDs. | Outcomes are `FAIL` or `NOT_EVALUABLE`; typed errors include not-found, `PROVENANCE_CONFLICT`, `DEPENDENCY_UNAVAILABLE`, and `INTERNAL_ERROR`; `SCHEMA_ERROR` is separate. | Consume explicit facts/claims/alignments only; never perform matching or parse prose in review. |
| 006 | `CoverageRun` binds run ID, source/version, resident context, source-fact extraction run, note/revision, claim set, `COVERAGE-CONTRACT-v1`, `COVERAGE_STATUS-v1`, `COVERAGE_EXPECTATION-v1`, `COVERAGE-RULESET-v1`, and idempotency key. | `SUCCEEDED` or `FAILED`; failures include malformed output, timeout, provenance conflict, dependency unavailable, and internal error. Unresolved items always require review. | Keep raw suggestions display-only and unresolved source items approval-blocking. |

All inspected transports share a `{code, message}` core. Optional `field`, `path`, and
`correlationId` fields are owner-specific contract extensions, not identity conflicts. Spec 007
uses its own OpenAPI error envelope and maps unavailable, malformed, failed, incomplete, or
provenance-mismatched upstream output to non-approval terminal states.

## Resolved compatibility decisions

1. Specs 003–006 do not provide one shared production router; Spec 007 uses injected
   reference-only ports and does not invent cross-spec HTTP endpoints.
2. Source text, note text, claim extraction, semantic matching, evidence verification,
   deterministic rules, and source coverage remain upstream-owned. Review consumes IDs, immutable
   metadata, and structured run results only.
3. Timeout/retry budgets remain upstream-owned. Review treats unavailable or malformed output as
   non-approval evidence and preserves the run reference for audit.
4. Review SQLite initialization is local and idempotent; no shared migration or cross-component
   transaction is assumed.
5. `tests/human_review` covers reference-only metadata stripping, malformed-result rejection,
   exact provenance checks, terminal failures, idempotency, and approval blocking; the full suite
   independently exercises upstream contracts.

T001/T002 are therefore evidenced by this report. Independent requirements-quality approval is
still pending and must be supplied by a reviewer; this document does not self-approve it.
