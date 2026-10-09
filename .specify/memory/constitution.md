<!--
Sync Impact Report
- Initial constitution: none -> 1.0.0
- Added principles: evidence fidelity, safety boundaries, spec-first delivery, contract-first architecture,
  layered verification, human review, test/evaluation rigor, privacy and provenance,
  observability and operational discipline.
- Added sections: Engineering Standards, Delivery Workflow, Quality Gates, Governance.
- Deferred: benchmark thresholds and model choices are intentionally feature-spec decisions.
-->
# AI Nursing Documentation Reliability Engine Constitution

## Core Principles

### I. Evidence Fidelity Is the Primary Product Invariant

- Every factual claim in a generated nursing note MUST be traceable to an immutable source transcript span or an explicitly authorized, versioned context source.
- The system MUST distinguish directly observed facts, caregiver-reported information, resident-reported information, uncertainty, negation, temporal qualifiers, and clinical interpretation.
- The system MUST NOT turn uncertainty into certainty, observations into diagnoses, or absent information into asserted facts.
- Numerical values, dates, quantities, residents, and units MUST remain faithful to source evidence. Exact and documented normalizations MAY be applied; conversions MUST preserve meaning and precision.
- Verification MUST distinguish `supported`, `unsupported`, `contradicted`, and `uncertain`. These labels MUST have versioned definitions and acceptance cases.
- An extracted claim MUST be atomic enough to evaluate independently. Compound statements MUST be split when their parts may have different evidence or outcomes.
- The system MUST check both directions: draft-to-source support and source-to-draft completeness for material information.

**Rationale:** Fluent output is not evidence of correctness. Source faithfulness is the system's central, testable value.

### II. Human Authority and Fail-Safe Review

- The application MUST function as a pre-approval quality gate, not an autonomous clinical decision-maker.
- Only an explicitly authorized human action MAY approve or reject a draft. The system MUST NOT silently approve, silently repair, or overwrite a caregiver's observations.
- Critical contradictions, unresolved resident assignment, unavailable verification, invalid evidence references, and other defined blocking issues MUST prevent approval until resolved under the review specification.
- Every approval MUST be bound to a specific draft revision and validation-run identifier. Any material edit MUST invalidate the prior approval and trigger revalidation of affected claims before re-approval.
- Flags MUST show a concise reason, severity, and relevant source evidence, or explicitly state that reliable evidence could not be established.
- The interface MUST distinguish a system finding from a confirmed clinical fact. Reviewers MUST be able to edit, reject, and record a resolution without losing the original draft or finding.

**Rationale:** Reliability assistance must increase informed human control rather than conceal uncertainty.

### III. Specifications Are Authoritative Before Implementation

- Every feature MUST have an approved, version-controlled specification describing purpose, scope, inputs, outputs, preconditions, behavior, error handling, dependencies, and acceptance criteria before implementation begins.
- The development sequence MUST be `constitution -> feature specification -> technical plan -> tasks -> tests -> implementation -> evaluation -> review`.
- Each normative requirement MUST have a stable identifier and MUST be traceable to at least one executable test or documented inspection method.
- Ambiguity affecting safety, evidence attribution, contracts, or approval MUST be resolved in the spec before coding; coding agents MUST NOT infer permissive behavior.
- Scope changes MUST update affected specs, test fixtures, and traceability records in the same change as the implementation.
- Non-goals MUST remain explicit: no diagnosis, treatment recommendation, automatic clinical decisions, real patient data, nursing-home software integration, or claim of regulatory certification in the PoC.

**Rationale:** Specifications prevent hidden assumptions and make engineering decisions reviewable.

### IV. Contract-First, Modular, and Deterministic Where Possible

- Pydantic models and OpenAPI contracts MUST define and validate all cross-component and API payloads; contract changes MUST be versioned and tested.
- Generation, claim extraction, evidence verification, deterministic validation, review policy, persistence, and presentation MUST have separate interfaces and independent tests.
- Structured claims MUST contain stable identifiers, resident identity or explicit unknown state, typed values where applicable, units, temporal/negation/attribution metadata, and provenance references.
- Source transcripts MUST be immutable within a validation run. Evidence spans MUST use documented offset semantics; the backend MUST verify that each cited span matches the stored source bytes or text under the declared normalization policy.
- Explicit rules MUST handle exact numeric comparisons, well-defined unit conversions, required identifiers, schema constraints, and evidence-span integrity. An LLM MUST NOT replace such deterministic checks.
- Conflicting findings from rule engines and LLM verifiers MUST be preserved. Policy MUST resolve them conservatively, with no silent downgrade of blocking rule failures.
- Pluggable model providers MUST be isolated behind versioned adapters. Infrastructure concerns MUST NOT leak into the domain validation policy.

**Rationale:** Stable contracts and testable boundaries reduce both software defects and opaque model failures.

### V. Evaluation Is a Release Gate, Not a Demo Accessory

- A versioned synthetic German benchmark of at least 100 scenarios MUST be maintained, including correct cases and injected errors across fabrication, numerical changes, negation, uncertainty, omissions, resident mixing, and unjustified clinical inference.
- Test cases MUST store source text, expected claim-level outcomes, evidence references, materiality/severity labels, and annotation provenance; disputed labels MUST be resolved and documented.
- Evaluation MUST separately measure critical-error recall, false-positive rate, claim classification performance, completeness, latency, inference cost, and reviewer workload, with stated denominators.
- Every model, prompt, ruleset, and dataset version MUST be recorded for each run. A held-out evaluation split MUST NOT be used for prompt tuning.
- The same test inputs MUST be used for baseline-vs-validated comparisons where feasible, and results MUST include raw counts and failure examples, not only percentages.
- A change MUST NOT be described as an improvement unless its relevant quality gates pass and regressions are disclosed. Synthetic benchmark performance MUST NOT be represented as clinical safety validation.
- Numerical release thresholds MUST be defined in `008-evaluation.md` before evaluation, including how to handle small sample uncertainty and repeated stochastic runs.

**Rationale:** Reproducible measurement prevents anecdotal success from masquerading as reliability.

### VI. Privacy, Provenance, and Auditable Decisions

- The PoC MUST use synthetic data only. Real patient or employee personal data MUST NOT enter model requests, logs, fixtures, screenshots, or demos.
- The system MUST record a tamper-evident or append-only logical history of source/version references, generated revisions, findings, rule/model/prompt versions, reviewer actions, timestamps, and final status.
- Logs MUST minimize content and secrets. Credentials MUST be provided through secure configuration and MUST NOT be committed to version control.
- Resident context MUST be explicitly labeled by source, trust level, version, and permitted use; unverified context MUST NOT be treated as transcript evidence.
- Data retention, deletion, access controls, and export behavior MUST be specified before moving beyond local synthetic-only operation.
- Regulatory compliance claims MUST NOT be made without a separate expert review and appropriately scoped evidence.

**Rationale:** Sensitive-domain prototypes need disciplined data handling and inspectable provenance from day one.

### VII. Observable Failures and Graceful Degradation

- Parsing errors, timeouts, unavailable model services, malformed responses, missing evidence, and incomplete runs MUST be explicit typed outcomes; they MUST NOT be interpreted as verification success.
- LLM calls MUST have defined timeouts, bounded retries, and idempotent run identifiers. Retrying MUST NOT duplicate reviewer actions.
- Production-like paths MUST emit structured metrics for latency, cost, token usage, rejection reasons, and warning counts without exposing sensitive text in telemetry.
- Severity policy MUST be explicit and independently testable; model confidence alone MUST NOT authorize approval.
- The user interface MUST expose pending, failed, and needs-review states accurately and MUST NOT imply that verification guarantees medical truth.

**Rationale:** A quality gate is trustworthy only if its own failures are visible and safe.

## Engineering Standards

- **Backend:** Python, FastAPI, Pydantic; business logic independent of HTTP handlers; dependency injection for model and storage adapters.
- **Frontend:** React with typed API clients and accessible, side-by-side source/draft/issue review; avoid color-only warning cues.
- **Storage:** SQLite for the local PoC; PostgreSQL MAY be introduced behind a repository interface without changing domain contracts.
- **Validation:** Pure deterministic functions wherever practical; explicit unit-normalization policy; stable machine-readable rule codes.
- **LLM integration:** Version prompts, model IDs, settings, structured output schemas, and request/response validation; use no model output as trusted evidence until verified.
- **Tests:** Unit tests for rules and state transitions; schema contract tests; API integration tests with mocked LLMs; scenario acceptance tests; versioned end-to-end evaluations.
- **Security:** Secret scanning, dependency vulnerability checks, input size limits, authentication/authorization for review endpoints when multi-user operation is introduced.
- **Documentation:** Architectural decisions crossing component boundaries MUST be captured in an ADR with alternatives and trade-offs.

## Spec-Driven Delivery Workflow

1. **Specify:** Create a feature spec with stable requirement IDs, source-of-truth semantics, examples, negative cases, and acceptance criteria. State assumptions and non-goals.
2. **Plan:** Define interfaces, data flow, affected components, privacy and safety considerations, verification strategy, observability, and trade-offs. Include a Constitution Check for every principle.
3. **Task:** Break the plan into small, independently verifiable vertical slices; link each task to requirements and tests.
4. **Test first:** Write deterministic acceptance/contract tests or labeled evaluation fixtures before implementing each slice.
5. **Implement:** Keep changes limited to the specified slice. AI coding agents MUST NOT introduce unapproved features, relax review policy, or rewrite contracts silently.
6. **Verify:** Run formatting, static analysis, unit, contract, integration, acceptance, and relevant benchmark tests; inspect claim evidence and failure paths.
7. **Review and merge:** Require a traceability update, documented deviations, benchmark regression summary for LLM-affecting changes, and reviewer sign-off.

## Quality Gates

A change is **not done** unless all applicable gates pass:

- **Specification gate:** Requirement IDs, acceptance examples, error conditions, and explicit review/approval behavior exist.
- **Contract gate:** Request/response schemas validate; backwards-incompatible changes have a migration or versioning plan.
- **Evidence gate:** Supported claims have valid provenance; invalid evidence offsets cannot be accepted as proof.
- **Safety gate:** Critical issues and verification failures cannot be auto-approved; edit/revalidation transitions are tested.
- **Rule gate:** Numeric, unit, identity, and schema rules pass unit and property/boundary tests.
- **Evaluation gate:** Relevant held-out scenario metrics and error counts are reported; configured thresholds pass or the change is explicitly held back.
- **Operational gate:** Timeouts, malformed outputs, logging, and retry behavior are tested for the affected boundary.
- **Documentation gate:** Specs, tests, traceability, prompt/model versions, and ADRs are updated when affected.

Exceptions MUST be documented with owner, rationale, risk, compensating control, and expiry. Exceptions MUST NOT bypass the human approval invariant, synthetic-only data constraint, or fail-closed handling of critical verification failures.

## Governance

- **Authority:** This constitution supersedes conflicting ad-hoc implementation conventions, prompts, and feature plans. Laws, binding policies, and higher-level safety obligations remain authoritative.
- **Amendments:** Changes require a written rationale, impact analysis, reviewer approval, version bump, and updates to affected templates/specifications in the same change. Reviewers MUST explicitly assess whether safeguards are weakened.
- **Versioning:** Use semantic versioning: MAJOR for incompatible governance changes or removed/redefined principles; MINOR for new principles or material expansions; PATCH for clarifications that do not change obligations.
- **Compliance:** Each implementation plan and pull request MUST contain a Constitution Check. Unresolved violations of MUST requirements block merge. Significant design deviations MUST have an ADR.
- **Reviews:** Revisit the constitution after major architecture or scope changes and before any transition from synthetic PoC to real-data research or production use. Such a transition requires a new approved scope and additional privacy, clinical, security, and regulatory assessment.
- **Ownership:** The project maintainer is the initial approval authority; clinical or compliance reviewers MUST be involved if the project scope expands into clinical deployment.

**Version:** 1.0.0 | **Ratified:** 2026-10-09 | **Last Amended:** 2026-10-09
