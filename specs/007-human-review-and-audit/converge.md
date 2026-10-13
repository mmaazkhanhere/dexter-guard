# Spec 007 — Backend Convergence Procedure

## 1. Purpose

Establish, with reproducible evidence, whether the **Human Review and Audit backend** satisfies the approved Feature 007 requirements, data contracts, invariants, acceptance criteria, and implementation tasks. Convergence is a verification decision, **not** an assertion that successful test commands alone prove completeness.

This document defines a repeatable review procedure. It does not claim that any check has been executed or that the current implementation is complete.

## 2. Scope and boundaries

**In scope:** backend domain services, Pydantic/API contracts, review decisions, finding severity, optional suggestions, immutable note revisions, claim-level and full-note re-verification coordination, approval/rejection controls, repository persistence, append-only audit history, upstream integration boundaries, and automated backend verification.

**Out of scope for this convergence review:** user-interface implementation and UI testing; speech recognition; multi-resident workflows; real patient data; diagnosis, treatment advice, or medical-truth verification; production authentication or authorization; EHR integration; distributed infrastructure; and overall benchmark/release claims owned by Spec 008. No out-of-scope work is to be added merely for completeness.

The backend must support the contractual operations required by a future client, but this review does not require or assess that client.

## 3. Sources of truth and traceability

Review the current approved versions of the following artifacts where present:

- `spec.md` and applicable clarifications: required behavior and acceptance scenarios.
- `data-model.md`: entities, relationships, revision and state invariants.
- `contracts/review-audit.openapi.yaml` and related schemas: externally observable API behavior.
- `plan.md`, `research.md`, and architecture decision records: implementation constraints and documented decisions.
- `tasks.md`: dependency-ordered work and test obligations.
- Applicable project constitution and Specs 001–006 interfaces, including `compatibility-review.md` when present.

Record the artifact version or commit used. A missing **required** artifact, unresolved conflict between approved artifacts, or undocumented interface assumption is a gap. Do not silently choose one conflicting source. Link every applicable FR, invariant, acceptance scenario, and task to code and verification evidence.

### Mandatory requirement coverage

| Requirement | Backend convergence proof |
| --- | --- |
| FR-15 | Critical/major/minor severity is assigned consistently under a documented policy. |
| FR-17 | Findings expose correct claim locations, transcript-version-bound source spans, and explanations through contracts. Visual highlighting is excluded. |
| FR-18 | Findings support independent, persisted decisions and appropriate state checks. |
| FR-19 | Manual corrections produce distinct note revisions without overwriting older content. |
| FR-20 | Suggestions are optional, evidence-grounded, explicitly accepted or rejected, and linked to resultant revisions when accepted. |
| FR-21 | Edited claims can be reverified; results are bound to the exact revision and cannot authorize final approval alone. |
| FR-22 | Approval requires a successful final **full-note** verification for the latest complete revision. |
| FR-23 | Unresolved critical discrepancies block approval through backend enforcement. |
| FR-24 | Approval, rejection, and reasoned adjudication are validated and persisted. |
| FR-25 | Prior note versions, findings, verification results, and review actions remain auditable. |

Also trace every applicable HR-001–HR-018 scenario (if defined in `spec.md`) and all relevant evidence-integrity invariants. Requirements implemented by upstream components must have verified integration contracts, not duplicate implementations here.

## 4. Convergence gates

### Gate A — Prerequisites and requirements integrity

1. Confirm the independent requirements-quality review is recorded, with reviewer, date, reviewed artifact revision, and outcome. Do not self-approve reviewer-owned checklist items.
2. Reconcile specifications, clarifications, contracts, models, plans, decisions, and task dependencies. Record contradictions and undecided semantics explicitly.
3. Confirm all applicable requirements and scenarios have implementation and test mappings. An unchecked task is not closed by a general statement that the test suite passes.

### Gate B — Contracts and upstream compatibility

1. Compare implemented routes, methods, request/response schemas, status codes, errors, and Pydantic validation with the approved OpenAPI contract.
2. Verify exact bindings among source document **ID/version**, note **ID/revision**, finding **ID**, claim set, and verification run; validate referenced entities before persisting decisions.
3. Verify terminal verification states, incomplete/malformed result behavior, timeouts, retries, idempotency replay/conflict rules, and expected-revision conflicts against the contracts.
4. Confirm integration with Specs 001–006 through actual interfaces or explicitly controlled test doubles. Document outstanding dependencies; do not infer unimplemented ports, schemas, or repository behavior.
5. Ensure the generated candidate note is never used as independent evidence for itself and source spans use the declared Unicode/offset semantics against the exact immutable transcript version.

### Gate C — Review lifecycle and evidence integrity

1. Confirm independent finding-level decisions, required adjudication reasons, and severity policy are enforced server-side.
2. Confirm suggestion acceptance is explicit; suggestion contents must be evidence-grounded, must not silently add unsupported facts, and must create or link to the appropriate successor revision.
3. Confirm every content-changing correction creates a new immutable note revision and invalidates the prior revision's approval eligibility; historical findings remain available for audit.
4. Confirm claim-level re-verification is informational for the affected revision and **cannot** substitute for final full-note verification.
5. Confirm final full-note verification covers the exact current note revision and claim set, and includes successfully completed applicable evidence, deterministic, and source-coverage checks from Specs 004–006.
6. Confirm unsupported evidence is distinguished from explicit contradiction. Missing or invalid evidence must not be converted into a supported finding.
7. Confirm verification failure, malformed output, missing required component results, timeouts, and stale or source-mismatched results leave the note unapproved.

### Gate D — Approval, rejection, concurrency, and audit

1. Exercise the backend approval predicate for completed/valid/full-note/current verification, required review-decision completeness, unresolved critical findings, and unresolved blocking source-coverage items.
2. Attempt approval with stale revisions, failed or incomplete verification, invalid component provenance, mismatched source versions, missing decisions, unresolved blockers, and concurrent edits; each must fail safely with a defined error.
3. Make the final revision check and approval disposition atomic in one transaction or through an equivalent concurrency-safe mechanism. An already approved/rejected final disposition must follow the documented immutability policy.
4. Confirm rejection remains possible when verification fails and that required reasons are stored.
5. Confirm append-only audit records preserve original revisions, generated findings, suggestions, reviewer labels, timestamps, decisions, reasons, verification provenance, and final dispositions. Updates must not silently erase history.
6. Verify durable persistence across process restart and idempotent requests do not create duplicate dispositions or contradictory audit histories.

### Gate E — Automated evidence and quality checks

Run the tests supported by the repository, including applicable:

- Schema/contract tests, domain-policy unit tests, repository and migration tests.
- API integration tests for revision creation, finding decisions, suggestion handling, claim-level re-verification, full-note verification, approval, rejection, and audit retrieval.
- Negative-path tests for invalid evidence, unsupported suggestions, malformed/time-out upstream responses, staleness, conflicts, and partial verification.
- Concurrency, transaction-atomicity, idempotency/retry, restart durability, and audit-history tests.
- End-to-end **backend** acceptance scenarios, including the full critical-discrepancy → correction → stale-run rejection → latest full-note re-verification → disposition and audit sequence.
- Static/compile checks, relevant observability checks, and repository diff hygiene (`git diff --check`) where available.

For each executed check, record **command, timestamp, code revision, environment/configuration, exit status, test counts, and non-sensitive result summary**. A missing test or inaccessible dependency must be recorded as `BLOCKED` or `NOT RUN`; never recorded as passing. Use synthetic test fixtures only.

## 5. Evidence ledger

Maintain a separate current-run report (for example, `convergence-report.md`) with one row for each requirement, invariant, acceptance scenario, and outstanding task:

| ID | Artifact reference | Implementation location | Test / evidence reference | Result | Owner / next action |
| --- | --- | --- | --- | --- | --- |
| FR-23 | `spec.md` approval criterion | _Populate during review_ | _Populate during review_ | NOT RUN | _Populate_ |

Permitted results: `PASS`, `FAIL`, `BLOCKED`, `NOT RUN`, and `NOT APPLICABLE` (with explicit rationale). Include the reviewed git revision and date. Evidence records must not contain real patient information or unnecessary transcript text.

## 6. Gap handling and iteration

1. Classify each non-passing item as an implementation defect, missing test/evidence, contract mismatch, documentation ambiguity, or external dependency.
2. For each concrete implementation or test gap, append or update a **single actionable, unchecked** task in `tasks.md`; reference requirement/scenario ID, observed evidence, dependency, files or component affected, and objective acceptance proof. Avoid duplicates.
3. Route specification or contract conflicts through explicit review and approval before changing the implementation baseline. Do not rewrite requirements merely to match existing code.
4. Do not silently mark independent reviews or task checkboxes complete. Re-run affected tests and the full applicable gates after remediation.
5. Keep dated results in the separate convergence report or history, not as contradictory “latest” sections in this procedure.

## 7. Decision rules

**CONVERGED** may be reported only if:

- All applicable requirements, integrity invariants, contracts, and backend acceptance scenarios have traceable, passing evidence on the reviewed revision.
- Independent required reviews are approved and recorded.
- Required tasks are completed with task-specific evidence; no unresolved blocking dependencies, undocumented contract drift, or constitutional violations remain.
- Final full-note approval, stale-result rejection, concurrency behavior, failure-safe handling, and append-only audit history are proven by automated tests.
- All `NOT APPLICABLE` exceptions have a documented scope justification.

**NOT CONVERGED** applies if any required gate fails, is blocked, lacks evidence, or remains unreviewed. Record the exact blockers and required next actions. Passing a broad test suite does **not** override a missing requirement, unchecked task, absent required check, or incompatible upstream contract.

**External project release distinction:** Completing Spec 007's backend convergence does not assert overall product readiness, clinical safety, or achievement of Spec 008's held-out benchmark thresholds. Those remain separate project-level decisions.

## 8. Execution record

Populate the separate convergence report with:

- Review date and reviewer
- Code commit/revision and artifact versions
- Environment and dependency revisions
- Requirement/test evidence ledger
- Failures, blocked items, and deviations
- Added or updated task IDs
- Final decision: `CONVERGED` or `NOT CONVERGED`
- Required follow-up actions and approver where applicable

**No convergence status is asserted by this procedure alone.**
