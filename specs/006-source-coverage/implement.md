# Spec 006 - Implementation Procedure

## Gate

Before implementation, read [checklist.md](checklist.md). If any item is unchecked, stop and request an independent reviewer complete the requirements-quality review. Do not edit checklist markers. This gate applies even when tasks appear straightforward.

## Procedure

1. Read the constitution, [spec.md](spec.md), [clarify.md](clarify.md), [data-model.md](data-model.md), [plan.md](plan.md), [ADR 005](../../docs/adr/005-source-coverage-boundary.md), OpenAPI contract, [tasks.md](tasks.md), and `compatibility-review.md` when T001 creates it.
2. Execute unchecked tasks strictly in dependency order, beginning at T001. Write the relevant contract/unit/acceptance test before each implementation slice.
3. Resolve only immutable upstream records. Reject copied request prose, stale/cross-bound references, invalid evidence, and incomplete provider output.
4. Keep deterministic integrity/policy code separate from extractor/matcher adapters. Deterministic code must not call a model, network, or make clinical/semantic inferences.
5. Treat `UNCERTAIN` as a source-linked decision limit only. Treat provider/schema/provenance/span/storage failures as failed runs with no authoritative partial result. Enforce the required 30-second timeout, two-attempt bound, idempotency-key replay/conflict rules, source hash/normalization check, and complete model/ruleset/dataset metadata.
6. Never edit note/source/claim data, assign final severity, or expose approval. Findings are source-derived review aids and must retain `requiresReview=true`.
7. Update only completed implementation task checkboxes with verification evidence; never change the reviewer-owned checklist.
8. Run T023 checks, arrange T024 independent review, then execute [converge.md](converge.md).

## Required invariants

- Valid source spans use exact Unicode code-point offsets and quotes are re-derived from the immutable transcript.
- Expected facts are source-only, atomic, typed, and policy-classified; unresolved source evidence never becomes an invented fact.
- Exactly one assessment covers every expected fact/unresolved item in a successful run; only faithful coverage contributes to completeness.
- A successful duplicate faithful claim prevents a false omission; a related distortion stays linked to Spec 004/005.
- Runtime extracted-fact counts are labelled and held-out metrics rely on manually annotated Spec 008 facts.
- Each note revision is independently evaluated and historical runs remain immutable.

