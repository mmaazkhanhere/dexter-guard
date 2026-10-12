# Spec 005 — Upstream and Downstream Compatibility Review

**Status:** Design-time mapping; implementation must revalidate in T001–T002.

| Component | Consumed / supplied artifact | Compatibility constraint |
| --- | --- | --- |
| Spec 001 | Exact `SourceDocument` and `SourceSpan` | Source is `(source_id, source_version)`; offset is zero-based, start-inclusive/end-exclusive Unicode code point; transcript remains immutable. Resolved evidence references add a run-unique ID without altering the canonical span. |
| Spec 002 | Candidate `note_id`, `note_revision` | Claim must identify its owning immutable note revision. Spec 005 does not edit it. |
| Spec 003 | Atomic normalized claim and stable `claim_id` | Measurement/approximation must be structured upstream; prose is not reparsed here. |
| Spec 004 | Optional explicit fact-to-claim alignment | Alignment is advisory provenance for comparability, not semantic evidence or a substitute source. No semantic logic is duplicated. |
| Spec 007 | `ValidationFinding` / `ValidationRun` | Renders rule, references, values, and `NOT_EVALUABLE`; owns final severity, blocking, resolution, and approval. |
| Spec 008 | Versioned rules/fixture manifest | Measures ruleset behavior; owns metrics, thresholds, and release judgement. |

If an upstream record cannot supply required structured measurement or alignment semantics, the adapter must expose the gap as `NOT_EVALUABLE` or a schema/provenance failure. It must not parse source prose to compensate.
