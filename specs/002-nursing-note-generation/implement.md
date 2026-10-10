# Implementation Record: Nursing Note Generation

## Gate status

**Not started.** The reviewer-owned `checklist.md` remains unchecked. Before implementation, complete T001 by reading `.specify/memory/constitution.md` and align all implementation paths with its required conventions.

## Required implementation invariants

- Every generated or imported note has a resolvable `sourceId` and exact `sourceVersion`.
- Imported `externalOrigin` identifies candidate provenance only; it is not evidence.
- Every successful result starts in `DRAFT` and is neither verified nor approved.
- Guardrail success means only that the generation contract was accepted; it is not evidence verification.
- Import invokes the generation adapter zero times.
