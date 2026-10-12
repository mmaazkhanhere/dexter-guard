# Spec 005 — Upstream and Downstream Compatibility Review

**Status:** Revalidated for implementation on 2026-10-12 (T001–T003).

| Component | Consumed / supplied artifact | Compatibility constraint |
| --- | --- | --- |
| Spec 001 | Exact `SourceDocument` and `SourceSpan` | Source is `(source_id, source_version)`; offset is zero-based, start-inclusive/end-exclusive Unicode code point; transcript remains immutable. Resolved evidence references add a run-unique ID without altering the canonical span. |
| Spec 002 | Candidate `note_id`, `note_revision` | Claim must identify its owning immutable note revision. Spec 005 does not edit it. |
| Spec 003 | Atomic normalized claim and stable `claim_id` | Measurement/approximation must be structured upstream; prose is not reparsed here. |
| Spec 004 | Optional explicit fact-to-claim alignment | Alignment is advisory provenance for comparability, not semantic evidence or a substitute source. No semantic logic is duplicated. |
| Spec 007 | `ValidationFinding` / `ValidationRun` | Renders rule, references, values, and `NOT_EVALUABLE`; owns final severity, blocking, resolution, and approval. |
| Spec 008 | Versioned rules/fixture manifest | Measures ruleset behavior; owns metrics, thresholds, and release judgement. |

## Repository mapping (T001)

| Concern | Existing convention | Spec 005 placement/decision |
| --- | --- | --- |
| Python package | Independent `src/<component>` packages with `__init__.py` exports | Add `src/deterministic_validation` as a domain component; keep rule evaluation free of FastAPI, repositories, and providers. |
| Contracts | Frozen Pydantic v2 models, `extra="forbid"`, snake_case fields with camelCase aliases where API-facing | `contracts.py` contains transport and resolved domain records plus version constants. |
| Persistence | Repository `Protocol` plus in-memory and SQLite implementations in component modules | Use injected snapshot/fact/claim/alignment repositories and an append-only in-memory run repository for the PoC; no new database migration is needed for the initial slice. |
| Services | Constructor injection for repositories, factories, clocks, and providers | `DeterministicValidationService` receives repositories, engine, run repository, and ID/clock factories. |
| API | `source_ingestion.app.create_app(...)` wires optional services and maps domain errors to JSON responses | Add the published `POST /api/v1/deterministic-validation-runs` route without changing existing routes. |
| Errors | Stable `StrEnum` codes and Pydantic payloads; handlers map errors to HTTP status | Add `SCHEMA_ERROR`, `ApiError`, and the Spec 005 operational error mapping. |
| Tests | `pytest`, `TestClient`, fake repositories/providers, contract/service/API layers | Add `tests/deterministic_validation` unit, contract, integration, acceptance, and repeatability coverage. |
| Tooling | `pyproject.toml` configures pytest only; no lint/type checker is configured | Run pytest, `python -m compileall`, and `git diff --check`; do not add tooling dependencies. |

## Upstream verification (T002)

- Spec 001 uses immutable `(source_id, source_version)` records and zero-based, start-inclusive/end-exclusive Unicode code-point spans.
- Spec 003 claims carry stable IDs and immutable note-revision identity; measurement structure is available only where upstream extraction supplies it, so Spec 005 will not parse prose.
- Spec 004 owns semantic alignment and exposes preselected pairs; Spec 005 consumes explicit alignment records and never performs semantic matching.
- The existing repository interfaces are not sufficient to resolve Spec 005 source facts and alignments, so the new component defines narrow injected protocols rather than changing upstream contracts.

## ADR review (T003)

ADR 004 is already **Accepted** and matches the published Spec 005 boundary: explicit preselected alignment, deterministic comparison only, independent evidence checks, and Spec 007 ownership of review policy. No amendment is required.

If an upstream record cannot supply required structured measurement or alignment semantics, the adapter must expose the gap as `NOT_EVALUABLE` or a schema/provenance failure. It must not parse source prose to compensate.
