# Spec 007 Implementation Tasks

**Execution gate:** The requirements-quality checklist has an architecture self-review, but
independent reviewer approval is still pending in
[requirements-quality.md](checklists/requirements-quality.md). A checked task records that its
implementation and task-specific evidence are present; it does not waive dependencies or the
independent-review gate for declaring overall convergence. T001-T002 evidence is recorded in the
compatibility review, while independent approval remains a separate governance gate.

**Dependencies:** Specs 001–006 contracts, the resolved integration decisions in [research.md](research.md), and the Spec 007 OpenAPI contract. `[P]` means independently parallelizable after listed dependencies.

## Phase 0 — Setup and existing-contract integration

**Spec Kit user-story convention:** Each task inherits the `[US#]` label assigned in the
User-story task structure table below; the mapping is authoritative for task traceability.

- [x] T001 Map actual router, SQLite repository, migration, and test conventions in `specs/007-human-review-and-audit/compatibility-review.md`. **Depends on:** independent checklist approval. **Requirements:** all. **Done when:** inspected interfaces and gaps are recorded without changing source code. **Evidence:** compatibility review route, persistence, and test-convention inventory; independent checklist approval remains a separate governance gate.
- [x] T002 Validate Specs 001–006 identities, error envelopes, and service availability against their actual contracts; verify the resolved integration decisions. **Target:** `compatibility-review.md`, `research.md`. **Depends on:** T001. **Requirements:** FR-15, FR-17, FR-21, FR-22. **Done when:** every adapter input is evidenced and no source-text/claim-text authority is invented. **Evidence:** compatibility review identity/version/error matrix and resolved reference-only adapter decisions.
- [x] T003 [P] Add focused synthetic German review fixtures for HR-001–HR-018, with immutable source/note/revision/run IDs and expected audit events, including unresolved-source-item approval blocking. **Target:** `tests/human_review/fixtures/`. **Depends on:** T002. **Requirements:** all. **Done when:** fixture manifest has no real data and maps every HR scenario to expected outcomes.
- [x] T004 [P] Add contract validation tests from `contracts/review-audit.openapi.yaml`, including terminal full-verification status, explicit 004/005/006 run IDs, suggestion-acceptance successor requirements, final-disposition conflict, error envelope, enum/version closure, conditional fields, and unknown-field rejection. **Target:** `tests/human_review/test_contracts.py`. **Depends on:** T002. **Requirements:** FR-15, FR-17–FR-25. **Done when:** proposed request/response schemas are testable and contract version is asserted.

## Phase 1 — Data models and persistence

- [x] T005 Define frozen Pydantic review domain models and policy/version constants from `data-model.md`. **Target:** `src/human_review/contracts.py`. **Depends on:** T002, T004. **Requirements:** FR-15, FR-18, FR-25. **Done when:** model validators enforce state separation, provenance equality, rationale requirements, and immutable terminal aggregate semantics.
- [x] T006 [P] Define repository ports and deterministic in-memory doubles for review records. **Target:** `src/human_review/repository.py`. **Depends on:** T005. **Requirements:** FR-19, FR-25. **Done when:** append-only interface supports revision/read/audit queries without upstream mutation.
- [x] T007 Implement SQLite review persistence using idempotent repository-local schema initialization, unique revision/disposition/idempotency constraints, and foreign-reference checks. **Target:** `src/human_review/repository.py`. **Depends on:** T005, T006. **Requirements:** FR-19, FR-24, FR-25. **Done when:** repository tests prove no update/delete path and historical records survive successor creation.
- [x] T008 [P] Write repository tests for append-only audit ordering, idempotency replay/conflict, revision uniqueness, immutable decisions, and synthetic-only fixtures. **Target:** `tests/human_review/test_repository.py`. **Depends on:** T006. **Requirements:** FR-18, FR-19, FR-25. **Done when:** the tests fail on overwrite/delete or duplicate conflicting writes.

## Phase 2 — Review retrieval and evidence highlighting (P1)

<!-- [US1] Inspect an evidence-grounded finding -->
- [x] T009 Implement `ReviewContextService` with source/note/claim/upstream-run readers and deterministic `REVIEW_SEVERITY-v1` mapping. **Target:** `src/human_review/context.py`, `policy.py`. **Depends on:** T002, T005. **Requirements:** FR-15, FR-17. **Done when:** it preserves upstream fields and yields exactly one severity per review finding.
- [x] T010 Implement source-span validation/excerpt derivation for review display; distinguish `AVAILABLE`, `MISSING`, and `INVALID` without fallback text search. **Target:** `src/human_review/context.py`. **Depends on:** T009. **Requirements:** FR-17. **Done when:** mismatched source version, offset, and quote tests cannot yield a highlight.
- [x] T011 [P] Write policy/context unit tests for contradiction, unsupported, uncertain, 005 rules, coverage keys, unknown types, and failed components. **Target:** `tests/human_review/test_policy.py`, `test_context.py`. **Depends on:** T009. **Requirements:** FR-15, FR-17, FR-23. **Done when:** every severity row and evidence availability state is asserted deterministically.

## Phase 3 — Finding-level decisions (P2)

- [x] T013 Implement append-only acknowledgement, dispute, and adjudication service with rationale/identity/idempotency validation and state projection. **Target:** `src/human_review/decisions.py`. **Depends on:** T005–T008, T009. **Requirements:** FR-18, FR-24, FR-25. **Done when:** no decision can mutate upstream finding or cross a note/revision boundary.
- [x] T014 Write decision state-transition tests, including acknowledgement of critical finding remaining open and non-critical documented adjudication. **Target:** `tests/human_review/test_decisions.py`. **Depends on:** T013. **Requirements:** FR-18, FR-23, FR-24. **Done when:** HR-003 and HR-013 pass with persisted rationale/timestamps/reviewer labels.
- [x] T015 Implement the finding-decision API route and typed request/response contract. **Target:** `src/human_review/api.py`, `src/human_review/contracts.py`. **Depends on:** T013, T004. **Requirements:** FR-18. **Done when:** `POST .../decisions` conforms to OpenAPI and returns persisted decision history.

## Phase 4 — Editing, revision tracking, and suggestions (P1/P3)

<!-- [US2] Correct and re-verify a note; [US6] Use a suggested correction safely -->
- [x] T016 Implement compare-and-append `RevisionService` using the existing note revision boundary, atomic audit append, and stale-result projection. **Target:** `src/human_review/revisions.py`. **Depends on:** T002, T007. **Requirements:** FR-19, FR-25. **Done when:** stale writer writes nothing and successor is `AWAITING_FULL_VERIFICATION`.
- [x] T017 Write revision/concurrency tests for manual edit, stale revision rejection, final-disposition immutability, preserved predecessor body, and old run staleness. **Target:** `tests/human_review/test_revisions.py`. **Depends on:** T016. **Requirements:** FR-19, FR-22, FR-25. **Done when:** HR-005 and HR-017 pass against SQLite/in-memory contract doubles and edits after approval/rejection return `FINAL_DISPOSITION_IMMUTABLE`.
- [x] T018 Implement structured correction validation, persistence, accept/reject decisions, and delegation to revision service. Treat raw Spec 006 suggestion strings as display-only; only a validated target span/replacement/source-support record can create a successor revision. **Target:** `src/human_review/suggestions.py`. **Depends on:** T010, T013, T016. **Requirements:** FR-20, FR-25. **Done when:** raw coverage suggestions cannot be applied and only validated corrections can create a successor revision.
- [x] T019 [P] Write suggestion tests for raw Spec 006 display-only wording, unsupported/unusable structured corrections, explicit acceptance with successor revision, stale base revision, and audit links. **Target:** `tests/human_review/test_suggestions.py`. **Depends on:** T018. **Requirements:** FR-20, FR-25. **Done when:** HR-004 and HR-011 pass and `SUGGESTION_ACCEPTED` cannot be persisted without a successor revision.
- [x] T020 Implement revision/suggestion API routes and typed request/response contracts. **Target:** `src/human_review/api.py`, `src/human_review/contracts.py`. **Depends on:** T015, T016, T018. **Requirements:** FR-19, FR-20. **Done when:** `201` successor and `409 STALE_REVISION` API contracts are verified.

## Phase 5 — Re-verification integration (P1)

<!-- [US2] Correct and re-verify a note; [US3] Safely approve or reject -->
- [x] T021 Define and implement the in-process Spec 003 extraction adapter, Spec 005-owned reference-only deterministic-validation adapter, and Spec 004/006 terminal-run adapters; validate exact source/note/claim-set provenance. **Target:** `src/human_review/ports.py`, `verification.py`. **Depends on:** T002, T005. **Requirements:** FR-21, FR-22. **Done when:** adapters use reference-only upstream inputs and never parse prose/reimplement algorithms.
- [x] T022 Implement claim-level re-verification aggregate marked `approvalEligible=false` and persist its feedback/audit reference. **Target:** `src/human_review/verification.py`. **Depends on:** T021. **Requirements:** FR-21, FR-25. **Done when:** HR-006 passes and claim-level response cannot enter approval predicate.
- [x] T023 Implement terminal full-note verification aggregate: fresh current claim set, explicit 004/005/006 component run references, component closure/provenance validation, failure/invalid outcomes, and idempotent retry. **Target:** `src/human_review/verification.py`. **Depends on:** T021, T007. **Requirements:** FR-22, FR-25. **Done when:** persisted aggregate has only `VALID`, `INVALID`, or `FAILED`; it is `VALID` only for complete same-source/same-revision successes; missing adapter/invalid output blocks it.
- [x] T024 Write service/integration tests for old-run invalidation, source mismatch, invalid output, provider/component failure, Spec 005 unavailable alignment, and final verification of latest revision. **Target:** `tests/human_review/test_verification.py`. **Depends on:** T022, T023. **Requirements:** FR-21, FR-22, FR-23. **Done when:** HR-006, HR-007, HR-012, HR-014, HR-016, and HR-017 pass.
- [x] T025 Implement full/claim verification routes and typed terminal status responses. **Target:** `src/human_review/api.py`, `src/human_review/contracts.py`. **Depends on:** T022–T024. **Requirements:** FR-17, FR-21, FR-22. **Done when:** endpoints match OpenAPI and claim feedback cannot enter the approval predicate.

## Phase 6 — Approval and rejection guards (P1)

<!-- [US3] Safely approve or reject -->
- [x] T026 Implement pure `ApprovalEligibilityPolicy` and atomic approval service transaction. **Target:** `src/human_review/approval.py`. **Depends on:** T013, T016, T023. **Requirements:** FR-23, FR-24. **Done when:** all six policy predicates in spec.md are re-evaluated server-side inside the write transaction.
- [x] T027 Implement rejection disposition service independent of verification success, requiring current revision, reviewer label, reason, idempotency, and audit event. **Target:** `src/human_review/approval.py`. **Depends on:** T007, T016. **Requirements:** FR-24, FR-25. **Done when:** failure-state rejection succeeds without an approval verification ID.
- [x] T028 Write direct API/service guard-bypass and concurrent edit/approve race tests. **Target:** `tests/human_review/test_approval.py`, `test_api.py`. **Depends on:** T026, T027. **Requirements:** FR-22–FR-25. **Done when:** HR-008, HR-009, HR-014, HR-015, HR-016 pass and no invalid approval row exists.
- [x] T029 Implement approve/reject routes and typed disposition/error responses. **Target:** `src/human_review/api.py`, `src/human_review/contracts.py`. **Depends on:** T026–T028. **Requirements:** FR-17, FR-24. **Done when:** API status/error responses are covered by contract and service tests.

## Phase 7 — Audit history, integration, and regression

<!-- [US5] Inspect an audit trail -->
- [x] T030 Implement ordered audit-history projection and retrieval endpoint. **Target:** `src/human_review/service.py`, `src/human_review/api.py`. **Depends on:** T007, T013, T016, T023, T027. **Requirements:** FR-25. **Done when:** original/corrected revisions, runs, decisions, suggestions, and disposition are returned without overwrite.
- [x] T031 Implement end-to-end synthetic German acceptance tests for HR-001–HR-018 and direct API bypass cases, including unresolved source-item blocking. **Target:** `tests/human_review/test_acceptance.py`. **Depends on:** T015, T020, T025, T029, T030. **Requirements:** all. **Done when:** every scenario in spec.md maps to an executable backend test and uses synthetic data only.
- [x] T032 [P] Add content-minimized observability and tests for IDs, versions, statuses, latency/retry/rejection counts, and no full source/note/prompt logging. **Target:** `src/human_review/observability.py`, `tests/human_review/test_observability.py`. **Depends on:** T023, T026. **Requirements:** FR-22, FR-25. **Done when:** constitution privacy/operational controls are asserted.
- [x] T033 Run focused and full tests, compile check, contract validation, and `git diff --check`; record actual commands/results in implementation evidence. **Target:** `specs/007-human-review-and-audit/convergence-report.md`. **Depends on:** T031, T032. **Requirements:** all / definition of done. **Done when:** commands pass and no undocumented deviation remains.
- [x] T034 Run read-only specification/task/contract convergence analysis; append only concrete gap tasks if found, implement them, and repeat to convergence. **Target:** `specs/007-human-review-and-audit/converge.md`. **Depends on:** T033. **Requirements:** all. **Done when:** analysis has no unresolved internal inconsistency; external dependencies remain explicitly tracked.

## User-story task structure

The task phases above are grouped by implementation dependency, while each group maps to the
following Spec Kit user stories. This mapping is the authoritative `[US#]` label for every
task in the listed range:

| User story | Task range | Outcome |
| --- | --- | --- |
| [US1] Inspect an evidence-grounded finding | T001–T011 | Review context, validated evidence, and severity |
| [US4] Record independent finding decisions | T013–T015 | Append-only acknowledgement, dispute, and adjudication |
| [US2] Correct and re-verify a note | T016–T025 | Immutable revisions and claim/full-note verification |
| [US6] Use a suggested correction safely | T018–T020 | Validated explicit-acceptance correction flow |
| [US3] Safely approve or reject | T026–T029, T036 | Atomic approval guards and rejection disposition |
| [US5] Inspect an audit trail | T030–T034 | Ordered audit history, integration, and regression evidence |

## Governance closure

- [x] T036 [P] [US3] Adopt or revise ADR 006 after T001–T002 compatibility evidence is available; record any ownership, transaction, timeout, retry, or error-contract deviation. **Target:** `docs/adr/006-human-review-and-audit-boundary.md`, `compatibility-review.md`. **Depends on:** T001, T002. **Requirements:** constitution Engineering Standards, FR-22–FR-25. **Done when:** the ADR has reviewer approval or an explicit documented exception with owner, risk, compensating control, and expiry. **Evidence:** ADR-006-E1 documents the owner, risks, compensating controls, and 2026-12-31 expiry; it is not independent reviewer approval.
- [x] T037 [US2] [US3] Implement the `/full-verifications` route and service boundary using the terminal `FullNoteVerification` contract, exact current claim/source/revision bindings, component-run references, malformed-output handling, and idempotent digest conflict behavior. **Target:** `src/human_review/api.py`, `src/human_review/verification.py`, `tests/human_review/test_verification.py`. **Depends on:** T021–T024. **Requirements:** FR-21, FR-22, HR-007, HR-014, HR-016. **Done when:** valid, invalid, failed, stale, malformed, and replay/conflict requests return the documented response without raising an untyped validation error.
- [x] T038 [US4] [US6] Expose structured suggestion retrieval and explicit suggestion-acceptance/rejection decisions through the API, including `suggestionId`, `expectedRevision`, successor-revision linkage, rationale rules, and idempotency. **Target:** `src/human_review/api.py`, `src/human_review/service.py`, `tests/human_review/test_api.py`, `test_context_and_suggestions.py`. **Depends on:** T013, T018–T020. **Requirements:** FR-18, FR-20, HR-003, HR-004, HR-011. **Done when:** raw Spec 006 suggestions remain display-only and accepted valid suggestions create one auditable successor revision through the documented contract.
- [x] T039 [US3] Complete `ApprovalEligibilityPolicy` and its transaction tests for policy-required decision/adjudication completeness, exact source and component-run provenance, current claim-set binding, unresolved Spec 006 source-item blocking, and all invalid/incomplete verification outcomes. **Target:** `src/human_review/approval.py`, `src/human_review/service.py`, `tests/human_review/test_approval.py`. **Depends on:** T023, T026–T028, T037. **Requirements:** FR-22–FR-24, HR-008, HR-014, HR-015, HR-018. **Done when:** direct API approval cannot bypass any documented predicate and concurrent revision changes write no disposition.
- [x] T040 [US5] Persist all review-owned entities (revisions, findings, decisions, suggestions, verification aggregates, dispositions, claim feedback, and audit events) through the SQLite repository with append-only constraints, foreign-reference checks, and restart/retrieval coverage. **Target:** `src/human_review/repository.py`, `tests/human_review/test_repository.py`. **Depends on:** T005–T008, T030. **Requirements:** FR-19, FR-24, FR-25. **Done when:** a repository restart preserves complete history and no review action can silently overwrite or delete an entity.
- [x] T041 [P] [US1] [US2] [US3] [US4] [US5] [US6] Add OpenAPI/schema and end-to-end synthetic German acceptance coverage for every documented backend endpoint and HR-001–HR-018, including direct API bypass, evidence validation, full verification, suggestions, approval/rejection, audit retrieval, and stale conflicts. **Target:** `tests/human_review/test_contracts.py`, `tests/human_review/test_acceptance.py`. **Depends on:** T003, T004, T015, T020, T025, T029, T037–T040. **Requirements:** all. **Done when:** the contract, API, and backend acceptance suites cover every route and scenario using synthetic German data only.
- [x] T042 [P] [US2] [US3] Add bounded timeout/retry, idempotency-digest, and content-minimized observability tests for every upstream adapter and review command. **Target:** `src/human_review/ports.py`, `src/human_review/verification.py`, `tests/human_review/test_observability.py`. **Depends on:** T002, T021, T032, T037. **Requirements:** constitution Principles IV, VI, VII; FR-21, FR-22, FR-25. **Done when:** unavailable/malformed providers produce typed terminal outcomes, retries do not duplicate actions, and telemetry contains no full source/note/prompt text.

## Requirement traceability

| Requirement | Scenarios | Primary tasks | Completion evidence |
| --- | --- | --- | --- |
| FR-15 | HR-001, HR-013, HR-014 | T009–T011 | Policy/unit tests and review-context contract |
| FR-17 | HR-001, HR-002 | T009–T011, T025, T029 | API/context evidence validation tests |
| FR-18 | HR-003, HR-013 | T013–T015 | State-transition and API tests |
| FR-19 | HR-004, HR-005, HR-017 | T016–T017, T020 | Immutable revision/concurrency tests |
| FR-20 | HR-003, HR-004, HR-011 | T018–T020 | Unusable/acceptance suggestion tests |
| FR-21 | HR-006 | T021–T025 | Claim response/approval-ineligible test |
| FR-22 | HR-007, HR-014, HR-016, HR-017 | T021–T025 | Exact latest-revision aggregate tests |
| FR-23 | HR-008, HR-014 | T026, T028 | Direct bypass guard tests |
| FR-24 | HR-008, HR-009, HR-013, HR-015, HR-016 | T013–T015, T026–T029 | Atomic disposition and rejection tests |
| FR-25 | HR-003, HR-010, HR-017 | T005–T008, T030–T032 | Append-only/audit history tests |
