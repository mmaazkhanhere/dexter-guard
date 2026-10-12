# ADR 005 - Source coverage extraction and semantic matching boundary

**Status:** Accepted  
**Date:** 2026-10-12  
**Deciders:** Dexter Guard maintainers

## Context

Spec 006 must detect important source facts that are absent or materially changed in a candidate nursing note. Source-fact extraction and German semantic matching may require a model, but model output cannot be trusted as evidence, cannot invent a fact, and cannot choose severity or approval. The constitution requires immutable provenance, versioned adapters, deterministic evidence-span checks, and preservation of conflicting findings.

## Decision

Spec 006 has two isolated provider ports:

1. A source-fact extractor returns atomic candidate facts or explicitly source-linked unresolved items. Deterministic validation requires an exact immutable source ID/version, resident context reference, source text hash, declared normalization policy, and valid spans. An uncited assertion is rejected; an unresolved item contains no asserted fact values.
2. A semantic coverage matcher compares resolved immutable source facts to the exact Spec 003 claim set. It returns structured relations and material-attribute differences, not a free-form status or severity. The deterministic orchestrator applies `COVERAGE_STATUS-v1`, validates closure, derives source quotes, and creates findings.

Every operation is bound to a run ID, required idempotency key, canonical input digest, correlation ID, provider/model/prompt/schema versions, `COVERAGE-RULESET-v1`, dataset version, and policy versions. Provider calls have a bounded timeout and retry count. A retry cannot create a second reviewer action or mutate a prior run.

Spec 004 and Spec 005 findings remain independent immutable records. Spec 006 stores validated correlation references and does not replace, downgrade, or recompute their outcomes. Spec 007 owns final severity and approval policy.

## Alternatives considered

| Alternative | Rejected because |
| --- | --- |
| Let the model return source facts without spans | Violates evidence fidelity and permits uncited invented facts. |
| Use keyword/string matching for German counterparts | Misses faithful paraphrases and mishandles qualifiers such as negation and uncertainty. |
| Let the matcher assign severity or approval | Violates human authority and makes policy model-dependent. |
| Merge coverage, evidence, and numeric findings into one status | Loses component ownership and can silently downgrade blocking findings. |
| Treat extractor failure as an empty fact set | Inflates completeness by hiding extraction omissions; failures remain explicit or source-linked unresolved. |

## Consequences

### Positive

- Semantic flexibility is available behind versioned adapters while evidence integrity remains deterministic.
- Exact source provenance, resident context, normalization, run identity, and retry behavior are auditable.
- Coverage, evidence, numeric, severity, and approval responsibilities remain separable and independently testable.

### Trade-offs

- A provider can return `UNCERTAIN` only through a valid source-linked unresolved item or structured unresolved match; malformed/timeout output fails the run.
- A faithful coverage result may coexist with an independent Spec 004/005 contradiction finding; Spec 007 must render and resolve the combination.
- Evaluation must retain manually annotated facts because extraction omissions cannot be measured from system facts alone.

## Compliance

This ADR governs `COVERAGE-RULESET-v1` and the `COVERAGE-CONTRACT-v1` boundary. Any change to source authority, span/normalization rules, retry/idempotency behavior, semantic relation classes, or finding ownership requires a versioned specification and ADR review.

