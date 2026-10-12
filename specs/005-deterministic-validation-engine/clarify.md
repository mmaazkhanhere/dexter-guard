# Spec 005 — Clarifications

**Status:** Resolved from supplied requirements and constitutional constraints  
**Method:** Decision log used to remove implementation-affecting ambiguity before planning. No semantic or clinical behavior is delegated to this engine.

| ID | Question | Decision folded into spec | Rationale |
| --- | --- | --- | --- |
| CL-001 | How are facts and claims paired? | Only an explicit upstream `ALIGNED` one-to-one alignment permits numeric comparison. An explicit `UNAVAILABLE`, `AMBIGUOUS`, or `REJECTED` alignment is `ALIGN-001` `NOT_EVALUABLE`; a missing or duplicate required alignment record rejects the run. | Prevents invented contradictions and avoids duplicate semantic matching. |
| CL-002 | Does Spec 005 decide semantic support? | No. Spec 004 owns semantic support/contradiction/uncertainty. Spec 005 may consume its alignment but retains independent rule findings. | Clear component boundary. |
| CL-003 | What counts as numeric equality? | Exact `Decimal` equality after documented conversion; no floating-point tolerance or clinically plausible range. | Faithful representation, not medical truth. |
| CL-004 | Which v1 units are compatible? | Fluid: ml/L; medication: mg/g; temperature: Celsius only; blood pressure: mmHg only. Conversion expands only by a new versioned ruleset. | Small, auditable PoC conversion catalog. |
| CL-005 | Are `ca.` and `genau` parsed from German text? | No. Approximation is a structured enum supplied upstream. `UNSPECIFIED` is not evaluable for NUM-004. | Prose keyword matching cannot reliably model uncertainty. |
| CL-006 | Does any numeric discrepancy have critical severity? | No. Engine emits a configured/default severity hint and `requires_review`; Spec 007 owns final severity and approval impact. | Keeps review policy outside Spec 005. |
| CL-007 | What happens if unit/category validation fails? | `STR-003` wins over conversion/comparison. The engine never compares values in invalid units. | Avoids misleading secondary mismatch. |
| CL-008 | How are malformed request fields different from a missing prerequisite? | Envelope/schema omissions reject with `SCHEMA_ERROR`; valid item records that lack a safe rule prerequisite receive individual `NOT_EVALUABLE` findings. | Separates invalid input from safe incomplete comparison. |
| CL-009 | What offsets and text equality apply? | Unicode code-point, zero-based, start-inclusive/end-exclusive offsets against the exact immutable Spec 001 transcript; quotation equality is exact, no display normalization. | Matches architecture and Spec 004 evidence contract. |
| CL-010 | Must evidence integrity wait for numeric alignment? | No. Each supplied evidence reference is independently checked, so invalid provenance cannot be accepted even when a comparison is not evaluable. | Evidence safety invariant. |
| CL-011 | Does the engine persist runs or expose an API? | It defines the versioned `POST /api/v1/deterministic-validation-runs` contract and an immutable run/result model. Router/module and persistence placement follow existing application conventions discovered in T001. | Contract-first without inventing a parallel platform. |
| CL-012 | How are multiple rules ordered? | Input alignment order followed by catalog order; structural prerequisites precede numeric rules and evidence rules execute independently. | Reproducible results and explainable precedence. |
| CL-013 | What happens when selected facts/claims have no alignment record? | Every selected fact and claim must appear in exactly one alignment record. `UNAVAILABLE`, `AMBIGUOUS`, or `REJECTED` produces the traceable `ALIGN-001` `NOT_EVALUABLE` result; a missing/duplicate record rejects the run. | Prevents empty successful validation and makes unavailable comparison explicit. |
| CL-014 | How are evidence references traced and how are value shapes represented? | Evidence references have stable run-unique IDs and every finding contains `evidence_reference_ids`. Scalars remain decimal text to allow `STR-001`; BP is a typed two-component object whose components may be invalid text only so `STR-001` can report it. | Completes traceability while retaining deterministic invalid-field reporting. |
| CL-015 | Where is an unsupported measurement category rejected? | The public request contains only immutable references. The resolver rejects an unknown category found in a referenced source fact or claim as `SCHEMA_ERROR`/provenance-invalid. | Aligns category validation with the reference-only public contract. |

## Remaining implementation choices (non-behavioral)

Repository module paths, migration syntax, router placement, and configuration object names must follow the existing Python/FastAPI/Pydantic/SQLite application at implementation time. They cannot change the published contracts, boundary, conversions, outcome semantics, or offset convention.
