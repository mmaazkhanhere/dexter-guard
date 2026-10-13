# Spec 008 Compatibility Review

**Review date:** 2026-10-13  
**Scope:** actual repository state on `main` before Spec 008 implementation

## Confirmed conventions

- Python package modules live under `src/<bounded_context>` and are discovered by Hatch; tests live under `tests/<bounded_context>`.
- Pydantic v2 contracts use frozen models, `extra="forbid"`, `populate_by_name=True`, camelCase aliases at transport boundaries, timezone-aware timestamps, and discriminated unions for terminal results.
- SQLite repositories initialize idempotently in their constructor, use append-only JSON payload rows, and protect idempotency keys with an input digest. Existing repositories reject a conflicting replay rather than overwrite a result.
- FastAPI application composition is bounded-context specific. No shared React host or frontend package exists in this checkout, so the required Spec 008 surface is headless Python plus an optional FastAPI router; no frontend is invented.
- Existing upstream workflows are synchronous terminal services. Provider retries are bounded and use one idempotent run identity; failures are typed and do not become successful findings.
- Existing source spans are zero-based, start-inclusive/end-exclusive Unicode code-point offsets bound to an immutable `(sourceId, sourceVersion)`.

## Actual upstream handoff points

| Upstream | Authoritative identity/result | Spec 008 use | Duplication forbidden |
|---|---|---|---|
| 001 source ingestion | `SourceDocument`, `SourceSpan`, source repository | preserve source/version/hash/span references | source validation or text replacement |
| 002 note generation | `NoteResponse`/`NoteRevisionRecord` | preserve note/revision/body hash and source identity | note generation or correction |
| 003 claim extraction | `ExtractionResult`, `Claim`, `extractionRunId` | map terminal claims/run metadata | claim extraction/scoring |
| 004 evidence verification | `VerificationRun`, `EvidenceFinding`, `verificationRunId` | map findings/status/discrepancy/spans | evidence verification |
| 005 deterministic validation | versioned validation run/finding contracts | preserve rule findings and run ID | deterministic rule logic |
| 006 source coverage | `CoverageRun`, `CoverageFinding`, coverage run ID | map expected-fact coverage findings | runtime completeness as ground truth |
| 007 human review | `FullNoteVerification`, `ReviewDecision`, audit records | store observed/simulated review outcome references | approval, repair, or review policy |

## Discovery gaps and decisions

1. The checkout contains no shared application factory or React client. Spec 008 therefore exposes a standalone `evaluation.api.create_router` and a Python runner/CLI; integration into a future host is dependency injection, not a new host.
2. Upstream service constructors are not uniform and no single composition root is present. The runner accepts a reference-only pipeline adapter protocol. It does not synthesize upstream findings or reimplement their business rules.
3. A protected benchmark must be usable without live upstream providers. The default dataset is a deterministic synthetic fixture; live adapters are opt-in and clearly labelled.
4. The reviewer-owned checklist amendment items remain unchecked. The user explicitly authorized implementation, so they are treated as review conditions and not falsely checked by implementation.

