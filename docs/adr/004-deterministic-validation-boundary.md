# ADR 004 — Separate deterministic comparison from semantic alignment

**Status:** Accepted  
**Date:** 2026-10-12  
**Deciders:** Dexter Guard maintainers

## Context

Spec 004 can use semantic reasoning to decide whether a source fact and nursing-note claim are meaningfully related and to identify meaning changes. Spec 005 must detect objective numeric, unit, structural, and evidence-reference errors deterministically. A naïve validator could parse transcript/note prose, use keyword or embedding matching, or ask an LLM to find counterparts before comparing numbers. That would duplicate semantic behavior, create conflicting outcomes, and turn absence of a reliable match into a false contradiction.

The constitution requires explicit rules for numeric/unit/schema/evidence checks, immutable source provenance, and deterministic behavior where possible.

## Decision

Spec 005 consumes normalized immutable facts and claims plus an explicit upstream alignment record. It evaluates numeric rules only when the alignment is one-to-one and `ALIGNED`; otherwise it returns a traceable `NOT_EVALUABLE` result. Evidence-reference integrity is checked independently of alignment.

Spec 005 uses no LLM, embedding, semantic retrieval, keyword matching, or clinical-range inference to decide counterpart identity, support, contradiction, diagnosis, or approval. It preserves its rule results beside—not inside—Spec 004 semantic evidence findings. Spec 007 owns how independent findings affect final review severity and approval.

## Alternatives considered

| Alternative | Rejected because |
| --- | --- |
| Let the deterministic engine find pairs with text keywords | German phrasing and scope vary; this silently recreates unreliable semantic matching. |
| Ask an LLM to establish pair identity before applying rules | Rule outcomes would depend on probabilistic inference and violate FR-16's deterministic boundary. |
| Compare every value of the same category | Multiple measurements can exist; this invents contradictions and fails evidence fidelity. |
| Make Spec 005 override Spec 004 status | Numeric/evidence findings and semantic status have distinct scope; overriding loses traceability and preempts Spec 007 policy. |

## Consequences

### Positive

- Numeric and evidence-integrity results are reproducible, independently testable, and explainable.
- Absence or ambiguity is safely visible rather than treated as an all-clear or fabricated mismatch.
- Semantic logic remains single-sourced in Spec 004; final policy remains single-sourced in Spec 007.

### Trade-offs

- Upstream extraction/alignment must provide explicit structured measurement and pairing data.
- Some true discrepancies remain `NOT_EVALUABLE` until alignment quality improves; this is intentional fail-safe behavior.
- Consumer views must render both semantic and deterministic findings rather than collapse them.

## Compliance

This ADR governs `DVE-RULESET-v1`. Any change that allows semantic pairing, changes a conversion or outcome policy, or merges finding authority requires a new versioned specification and ADR review.
