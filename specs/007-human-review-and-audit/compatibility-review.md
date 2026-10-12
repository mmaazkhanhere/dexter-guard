# Spec 007 Compatibility Review

**Status:** T001-T002 have documented inspection results but remain unchecked pending
independent requirements-quality approval; implementation compatibility is partially available
and remaining adapter gaps are explicit below.

The concrete repository was inspected on 2026-10-12. Existing implementations are local
Python modules with frozen Pydantic contracts, in-memory repositories, SQLite note/source
repositories, and FastAPI adapters. Spec 007 uses injected ports for the missing aggregate
boundary rather than inventing upstream HTTP endpoints.

Before T005 or any dependent implementation begins, T001–T002 must record, for each upstream
specification:

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

Until this report is completed, no implementation task may claim upstream integration
compatibility or approval readiness.

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
