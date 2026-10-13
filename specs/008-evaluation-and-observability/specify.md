# Specify Record — Spec 008

## Feature statement

Provide the reproducible measurement and observability system for the AI Nursing Documentation Reliability Engine. It evaluates the existing source-grounding pipeline on a versioned synthetic German benchmark, compares paired baseline and validated workflows, records operational trade-offs, and exposes inspectable results.

## Why this feature exists

Specs 001–007 make source-grounded extraction, verification, deterministic validation, coverage checking, and human review possible. Spec 008 establishes measurable evidence of how those existing capabilities perform and whether a change regresses them. Its output is a benchmark result, not a clinical-safety assertion.

## Governing constraints

- The constitution, `docs/architecture.md`, and approved Specs 001–007 govern terminology, immutable provenance, evidence-status meaning, and ownership.
- Only synthetic German data is permitted.
- The feature consumes pipeline outputs; it never duplicates the engines owned by Specs 003–006 or the review/approval policy owned by Spec 007.
- A held-out split is protected from prompt/model/rule tuning and model selection.
- The sole approved performance target is held-out critical-error recall of at least 95%; other thresholds are `TBD`.

## Authoritative specification

[spec.md](spec.md) defines the feature behaviour and acceptance scenarios. [clarify.md](clarify.md) resolves material requirements ambiguity before planning; [data-model.md](data-model.md), [contracts/evaluation.openapi.yaml](contracts/evaluation.openapi.yaml), and [plan.md](plan.md) provide design detail without changing product requirements.
