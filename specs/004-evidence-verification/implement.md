# Spec 004 — Implementation Procedure

**Purpose:** Execute [tasks.md](tasks.md) in dependency order without weakening safety or altering reviewer-owned checks.

## Mandatory preflight gate

1. Read spec.md, clarify.md, annotation-policy.md, contracts/verification-runs.openapi.yaml, plan.md, tasks.md, analyze.md, the constitution, and docs/architecture.md.
2. Read every checkbox in checklist.md.
3. If any required checklist item is unchecked, stop before code changes and ask the designated reviewer to complete the requirements-quality review.
4. Do not edit checklist.md, check checklist items, or treat task completion as reviewer approval.
5. When the checklist is approved, complete T001 first and map all planned components to the repository’s existing locations.

At generation time, checklist.md deliberately has unchecked reviewer-owned items. Therefore an implementation run started now must stop at step 3; it must not build a partial verifier.

## Execution order

1. Complete Phase 0 in tasks.md and commit/review schema decisions before model integration.
2. Complete deterministic source-span and provenance controls in Phase 1, with their unit tests passing first.
3. Complete the structured verifier boundary and deterministic response validation plus annotation-policy application in Phase 2. Treat every model response as untrusted; deterministic code must not independently infer semantic support or contradiction.
4. Add immutable run persistence and orchestrate the all-or-nothing lifecycle in Phase 3.
5. Add the authenticated POST endpoint and the German-language regression suite in Phase 4.
6. Complete telemetry, privacy checks, operations documentation, and Spec 008 fixture handoff in Phase 5.
7. Execute all project-required checks in T029, then ask the reviewer to perform T030.
8. Run the convergence procedure in converge.md. Implement only tasks appended by that procedure, then repeat until it reports convergence.

## Non-negotiable implementation constraints

- Do not use the generated note, any other claim, retrieval ranking, or model memory as independent evidence.
- Do not classify timeout, malformed output, invalid offsets, stale source version, missing claim coverage, or persistence error as UNCERTAIN, UNSUPPORTED, or any other evidence status.
- Do not accept a verifier quotation without deriving and comparing it from the immutable source span.
- Do not normalize, repair, or silently substitute source text, source versions, claims, or note revisions.
- Do not add numerical/unit judgment, completeness analysis, approval decisions, or audit decisions to this feature.
- Do not return a success response with partial findings. A claim set succeeds only when every valid claim has one validated primary status.

## Completion evidence

Before declaring Spec 004 implemented, attach:

- schema/contract validation results;
- unit, integration, API, and EV-001 through EV-014 regression results;
- evidence that malformed model responses and timeouts are non-successful;
- evidence that quotation mismatch and stale source version cannot succeed;
- model, prompt, and annotation-policy version capture;
- reviewer checklist decision;
- final convergence report.
