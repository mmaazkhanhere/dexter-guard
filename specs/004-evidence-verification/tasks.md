# Spec 004 — Implementation Tasks

**Source artifacts:** [spec.md](spec.md), [clarify.md](clarify.md), [annotation-policy.md](annotation-policy.md), [contracts/verification-runs.openapi.yaml](contracts/verification-runs.openapi.yaml), [plan.md](plan.md), and [checklist.md](checklist.md)
**Execution rule:** Do not begin implementation until the reviewer-owned checklist gate is satisfied. Tasks are dependency ordered; [P] means work may proceed in parallel after its listed dependencies.

## Phase 0 — Architecture and contract baseline

- [ ] T001 Read the constitution and architecture document; map this plan to the existing backend module, API router, persistence, migration, configuration, model-client, fixtures, and test locations. Record the mapping in the PR description. No new platform or parallel service.  
  **Depends on:** none
- [ ] T002 [P] Inspect Specs 001–003 contracts and fixtures. Document the exact source snapshot, note revision, claim-set, and normalized-claim fields available to verification.  
  **Depends on:** T001
- [ ] T003 [P] Inspect Specs 005–008 interfaces to confirm numerical/unit checks, omissions, approval, and evaluation remain outside this module.  
  **Depends on:** T001
- [ ] T004 Define the versioned Pydantic and OpenAPI public/internal schemas for EvidenceStatus, SourceSpan, EvidenceFinding, VerificationRun, request, and structured failure. Use the architecture's canonical SourceSpan fields (`source_id`, `source_version`, `start`, `end`), define the explicit transport mapping if needed, include derived quotations only alongside spans, evidence-status-policy version, annotation-policy version, idempotency key, model/prompt identity, timestamps, and correlation ID, and encode enum closure and success/failure exclusivity.
  **Depends on:** T001, T002
- [ ] T005 Write Pydantic service-validator and API contract tests before service implementation. Enforce distinct submitted claim IDs; exact, unique response coverage with no missing or foreign claim IDs; success/failure exclusivity; valid end-exclusive Unicode source offsets; source-derived quotation-to-span equality; successful `UNSUPPORTED` findings with no spans or only `CONTEXT_NON_SUPPORTING` context; and invalid required-span failure responses.
  **Depends on:** T004

## Phase 1 — Deterministic integrity foundation

- [ ] T006 Implement the shared source-text indexing utility using the published zero-based, start-inclusive, end-exclusive Unicode code-point convention. Preserve the exact source string.  
  **Depends on:** T004
- [ ] T007 Write unit tests for T006 using German umlauts, combining characters, emoji/non-BMP characters, whitespace, punctuation, line breaks, empty ranges, and out-of-bound ranges.  
  **Depends on:** T006
- [ ] T008 Implement SourceSpan and quotation validation: source ID/version equality, integer/range checks under zero-based end-exclusive Unicode code-point indexing, source substring derivation, quotation-to-span equality, and rejection of verifier quotation mismatch.
  **Depends on:** T006
- [ ] T009 Write integrity tests for valid span, stale source identity, reversed/empty/out-of-range offsets, end-exclusive boundary behavior, mismatched quotation, and invalid `CONTEXT_NON_SUPPORTING` pairing. Cover EV-010.
  **Depends on:** T008
- [ ] T010 Implement input and provenance validation against existing source, note, and claim repositories. Enforce non-empty claim set, unique claim IDs, exact source version, exact note revision, claim ownership, required resident identity/`UNKNOWN` handling, and known-resident equality with the source.
  **Depends on:** T002, T004
- [ ] T011 Write repository-backed tests for missing transcript, EV-011 source-version mismatch, unknown claim, duplicate claim, and cross-note/cross-revision claim rejection.  
  **Depends on:** T010

## Phase 2 — Semantic-verifier boundary and policy

- [ ] T012 Define the semantic-verifier port and strictly schema-validated response object. It accepts claims and source-only evidence; it cannot persist, approve, or mutate upstream records.  
  **Depends on:** T004, T010
- [ ] T013 Implement advisory candidate-evidence discovery using claim text and upstream normalized attributes. Ensure short transcripts can be supplied in full and retrieval absence never decides status.  
  **Depends on:** T012
- [ ] T014 Implement the approved model adapter using structured output, configured timeout, bounded safe retry policy tied to the same idempotent run identifier, model/prompt version capture, and redacted diagnostics.
  **Depends on:** T012, T013
- [ ] T015 Write adapter contract tests with a deterministic fake for malformed JSON, invalid enum, duplicated/missing/foreign claim IDs, missing explanation, timeout, and provider failure. Cover EV-012.  
  **Depends on:** T014
- [ ] T016 Implement deterministic response validation and EVIDENCE_ANNOTATION-v1 application: enum/contract validation, coverage enforcement, required spans by status, required discrepancy labels, and qualifier-policy handling. The semantic verifier—not deterministic code—classifies semantic support, contradiction, or uncertainty. Preserve conflicting verifier/rule findings and resolve only documented mechanical policy constraints conservatively.
  **Depends on:** T008, T014
- [ ] T017 Write policy unit tests for explicit contradiction, absent support, genuine ambiguity, certainty escalation, explicitly unconfirmable certainty claim, patient-report attribution escalation, unsupported clinical inference, negation reversal, and partial negation.  
  **Depends on:** T016

## Phase 3 — Verification run orchestration and persistence

- [ ] T018 Create the immutable VerificationRun persistence model and repository/migration using the existing storage conventions. Enforce one finding per run and claim and preserve all mandatory provenance/version metadata.  
  **Depends on:** T004, T010
- [ ] T019 Implement run lifecycle transitions: RECEIVED, VALIDATING, VERIFYING, SUCCEEDED, and every defined terminal failure. Ensure only SUCCEEDED has authoritative findings.  
  **Depends on:** T016, T018
- [ ] T020 Implement the verification application service in the algorithm order from plan.md: validation, immutable lookup, discovery, verifier call, response validation, span validation, normalization, coverage, atomic persistence.  
  **Depends on:** T019
- [ ] T021 Write integration tests proving all-or-nothing behavior: one failing claim, invalid evidence in one finding, missing/duplicate/foreign findings, persistence failure, and no approved/authoritative partial output. Prove that an invalid required span fails the whole run while a contract-valid `UNSUPPORTED` claim with no span or only valid `CONTEXT_NON_SUPPORTING` context remains a successful finding.
  **Depends on:** T020

## Phase 4 — HTTP API and end-to-end regression suite

- [ ] T022 Add POST /api/v1/verification-runs to the existing API router, its versioned OpenAPI contract, error-envelope, required idempotency, and correlation conventions. Use a local synthetic-demo access boundary and data minimization; do not add accounts, roles, permissions, authentication, or authorization.
  **Depends on:** T020
- [ ] T023 Write API contract tests for successful response, invalid HTTP request, identifiable failed run, response-schema stability, findings/failure exclusivity, required public execution metadata (model/prompt identity, timestamps, correlation ID, and policy versions), and minimum evidence exposure at the applicable review boundary.
  **Depends on:** T022
- [ ] T024 Create versioned German-language fixtures and expected findings for EV-001 through EV-014. Each test asserts the `EVIDENCE_ANNOTATION-v1` policy version, claim ID, canonical primary status, required discrepancy labels, span boundaries/text where required, and run state.
  **Depends on:** T017, T023
- [ ] T025 Add end-to-end tests over immutable source, note revision, extracted claim fixtures, deterministic verifier fake, persistence, and API. Verify all functional requirements FR-07 through FR-13 in scope. Add a separately marked real-configured-verifier development acceptance suite over the fixed synthetic development dataset: assert primary status, discrepancy labels, and evidence integrity, record failures and versions, and never assert exact explanation wording. Held-out evaluation remains Spec 008.
  **Depends on:** T024

## Phase 5 — Operations, privacy, and evaluation handoff

- [ ] T026 Add structured telemetry for lifecycle, latency, inference cost, token usage, model/prompt/policy versions, rejection reasons, warning counts, span-integrity failures, coverage failures, and safe failure codes. Confirm transcripts/prompts/raw model output are redacted according to architecture policy.
  **Depends on:** T020
- [ ] T027 Document configuration, approved verifier settings, timeout/retry behavior, run retention, and operational troubleshooting in the project’s standard operations location.  
  **Depends on:** T014, T026
- [ ] T028 Package the labeled synthetic fixtures and result export needed by Spec 008 to measure classification error and false positives without adding evaluation logic to the online request path.  
  **Depends on:** T024
- [ ] T029 Run the project’s required formatter, static checks, unit tests, contract tests, integration tests, and regression suite. Attach outcomes to the PR.  
  **Depends on:** T025, T026, T027, T028

## Phase 6 — Completion verification

- [ ] T030 Re-run the reviewer-owned requirements checklist; a human reviewer updates it if satisfied. The implementation flow must not change checklist markers.  
  **Depends on:** T029
- [ ] T031 Run the convergence procedure in converge.md. If it identifies gaps, append only new tasks, implement them, and re-run until convergence is reported.  
  **Depends on:** T030

## Dependency summary

~~~text
T001 → T002/T003 → T004 → T005/T006/T010/T012
T006 → T007/T008 → T009/T016
T010 → T011/T012/T018
T012 → T013 → T014 → T015 → T016 → T017
T018 + T016 → T019 → T020 → T021/T022/T026
T022 → T023 → T024 → T025
T024 → T028
T014 + T026 → T027
T025 + T026 + T027 + T028 → T029 → T030 → T031
~~~
