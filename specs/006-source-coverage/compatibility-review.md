# Spec 006 - Upstream and Downstream Compatibility Review

**Review date:** 2026-10-12  
**Purpose:** Record contract compatibility evidence before implementation. This is a repository inventory, not a substitute for missing Spec 007/008 contracts.

## Available contracts verified

| Dependency | Verified identifiers and fields | Spec 006 integration rule |
| --- | --- | --- |
| Spec 001 | `sourceId`, `sourceVersion`, immutable transcript, zero-based start-inclusive/end-exclusive source spans | Coverage validates the exact source version, hash, and normalization policy; it never changes span identity. |
| Spec 003 | `Claim.id`, `noteRevisionId`, `residentTestId`, polarity/certainty/attribution/temporal metadata, extraction-run identity | Coverage uses the immutable extraction run as `claimSetId` and validates exact note/revision/resident binding. |
| Spec 004 | `EvidenceFinding.claimId`, `status` (`SUPPORTED`/`UNSUPPORTED`/`CONTRADICTED`/`UNCERTAIN`), `sourceSpans`, `evidenceQuotes`, `verificationRunId`, source/note/revision fields | Coverage stores immutable `SPEC_004` finding references only; its `COVERAGE_STATUS-v1` namespace remains separate. |
| Spec 005 | `ValidationFinding.ruleId`, `sourceFactId`, `claimId`, `alignmentId`, `evidenceReferenceIds`, `outcome`, `rulesetVersion`; `ValidationRun` source/note/revision binding | Coverage stores immutable `SPEC_005` finding references and does not reimplement numeric/unit rules. |

## Missing downstream specifications

No `specs/007-*` or `specs/008-*` directory is currently present. Final severity/approval compatibility and benchmark/release-threshold compatibility therefore cannot yet be proven.

Before T013, T021, or T022 can be accepted, the designated owner must supply and review:

- Spec 007 severity-policy key mapping, finding-resolution/approval contract, and reviewer-action identifiers.
- Spec 008 benchmark-case schema, 100+ scenario dataset version, annotation provenance/dispute fields, held-out split rules, and release thresholds.

Until those contracts exist, implementation may proceed only through repository mapping and contract scaffolding. The current policy-key handoff is not proof of downstream compatibility.

## Required pre-implementation checks

1. Verify exact field aliases and revision semantics against the supplied Spec 007/008 contracts.
2. Verify `severityPolicyKey`, `relatedFindingRefs`, `datasetVersion`, and `requiresReview` map without lossy conversion.
3. Verify Spec 007 preserves independent Spec 004/005 findings and never treats `COVERED` as approval.
4. Verify Spec 008 evaluates manually annotated facts rather than system-extracted facts and records all constitution-required metrics.
5. Record any contract changes in this review, `spec.md`, the OpenAPI contract, fixtures, and tasks before implementation.

