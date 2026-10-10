# ADR 002: Nursing-note generation boundaries

## Status

Accepted for the synthetic Spec 002 proof of concept.

## Context

Spec 002 must create editable German nursing-note candidates and structured candidate facts while keeping source evidence, verification, and approval as separate concerns. The repository already provides a Python/FastAPI/Pydantic source-ingestion boundary with deterministic in-memory persistence for local tests.

## Decision

- Keep the implementation in Python with FastAPI and Pydantic contracts.
- Reuse the Spec 001 source service as the only source/version resolver; note records cannot be created from unreferenced transcript text.
- Isolate generation behind a small `GenerationAdapter` protocol. The default application has an explicit unavailable-provider failure. CI uses `DeterministicNursingNoteAdapter`, which is labeled as a test double and is not live-model functionality.
- Persist generated and imported revisions behind `NoteRepository`. The local proof of concept uses an in-memory implementation consistent with the existing Spec 001 persistence boundary; a durable store can be added behind the protocol without changing the API contracts.
- Validate provider output with Pydantic first and then apply bounded, deterministic checks for source anchors, numeric/unit fidelity, explicit negation, uncertainty, attribution, resident identity, and newly introduced unsupported diagnoses. Passing these checks is not verification or clinical truth.
- Keep import as a separate service path. It preserves supplied content exactly, accepts only externally supplied facts, and does not depend on or invoke the generation adapter.
- Create all revisions as `DRAFT`; approval and verification remain downstream responsibilities.

## Consequences

This boundary is deterministic and testable without network access or paid model calls. The limited guardrails can reject defined fixture regressions but cannot establish general semantic equivalence or clinical correctness. The existing in-memory repository is appropriate for the synthetic local proof of concept and is not a production persistence claim.
