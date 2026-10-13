# Spec 007 Technical Plan — Human Review and Audit

**Input:** [spec.md](spec.md), [clarify.md](clarify.md), constitution, [architecture.md](../../docs/architecture.md), and Specs 001–006.  
**Outcome:** A local, append-only human review workflow that coordinates existing verification services without duplicating their algorithms.

## Technical context

| Concern | Selected context |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Pydantic v2; domain services independent of HTTP. |
| UI | Desktop-oriented React with typed API client; accessible side-by-side transcript/note/finding review; no color-only indicators. |
| Persistence | Existing repository abstraction and SQLite for the local synthetic PoC; in-memory repository doubles for tests. |
| Existing verification | Spec 003 claim extraction; Spec 004 `POST /api/v1/verification-runs`; Spec 005 `POST /api/v1/deterministic-validation-runs`; Spec 006 `POST /api/v1/coverage-runs`. |
| Source/evidence semantics | Immutable source `(sourceId, sourceVersion)` and zero-based, code-point, start-inclusive/end-exclusive spans. |
| Authentication | Deliberately absent. Request `reviewerLabel` is synthetic PoC attribution only. |

## Architecture and component boundaries

```text
React Review UI
  └─ Review API (/api/v1/reviews/*)
       ├─ ReviewContextService ── source/note/claim/run readers
       ├─ RevisionService ─────── NoteRepository append successor
       ├─ FindingDecisionService ─ ReviewRepository append events
       ├─ VerificationOrchestrator
       │    ├─ ClaimExtractionPort (Spec 003)
       │    ├─ EvidenceVerificationPort (Spec 004)
       │    ├─ DeterministicValidationPort (Spec 005)
       │    └─ SourceCoveragePort (Spec 006)
       ├─ ApprovalService ────── atomic eligibility + disposition
       └─ AuditService ───────── append-only event projection
                 │
                 └─ SQLite ReviewRepository + immutable upstream references
```

| Component | Responsibility | Must not do |
| --- | --- | --- |
| Review context/read model | Load exact source/note revision, claims, upstream runs, mapped findings, decisions, suggestions, and status; derive display excerpts only after span validation. | Infer evidence, repair spans, mutate upstream records. |
| Severity policy | Convert immutable upstream finding metadata into a Spec 007 severity with policy version and mapping rationale. | Use LLM confidence/clinical judgement or overwrite upstream status. |
| Revision service | Compare expected revision and append an immutable successor plus audit event. | Update a note body in place, auto-verify, or merge concurrent text. |
| Suggestion service | Persist source-grounded suggestions and accept/reject them; acceptance delegates to revision service. | Apply a suggestion automatically or allow unsupported text. |
| Finding decision service | Append acknowledgement/dispute/adjudication/manual-correction-link events and project finding state. | Alter original upstream finding/run. |
| Verification orchestrator | Build exact immutable input references and call/upstream adapters, then persist a full-note verification aggregate. | Re-implement extraction, semantic verification, deterministic rules, or coverage matching. |
| Approval service | In one transaction, re-check latest revision, valid bundle, critical findings, and required decisions before writing approval. | Trust UI status or a claim-level run. |
| Disposition/audit service | Append approval/rejection and ordered audit events. | Delete, rewrite, or hide prior events. |

## Integration dependencies and required adapter contracts

The following are real dependencies; implementation must confirm them rather than assume them.

| Dependency | Available inspected boundary | Required Spec 007 adapter / gap |
| --- | --- | --- |
| Source resolver (001) | Source service/repository and source-span resolver; immutable identities exist. | `get_source(sourceId, sourceVersion)` and validated span resolution. |
| Note repository (002) | `NursingNoteService.create_revision` and repository conventions exist; note APIs cover generate/import. | Revision adapter must accept expected revision and create immutable successor with reviewer label; do not invent a mutation endpoint. |
| Claim extraction (003) | `ClaimExtractionService.extract_claims` and immutable claim repository exist. | Inject the local in-process `ClaimExtractionPort.extract(noteRevisionId)` and retrieve the exact claim set. No new public endpoint is introduced. |
| Evidence verification (004) | Published synchronous terminal HTTP contract and `VerificationService.verify`. | Adapter sends the resolved current claim set with a fresh idempotency key and records returned run ID. |
| Deterministic validation (005) | Published run endpoint/service; requires source facts, claim IDs, and explicit alignments. | A Spec 005-owned `DeterministicValidationPort.run_for_revision` resolves existing immutable source facts/explicit alignments then invokes the service. Spec 007 supplies references only and never builds alignments from prose. |
| Source coverage (006) | Published terminal run endpoint/service; consumes source-fact extraction run and claim set. | Adapter builds only documented reference-only request. The extraction run is an explicit prerequisite. |
| API host | `source_ingestion.app.create_app` wires optional upstream services. | Add a separate review router/dependency injection, only after a review service exists; no current review route is claimed. |

## Review workflow orchestration

### Retrieve context

1. Resolve note and requested/current revision; resolve its immutable source reference.
2. Load source text only for the authorised review response, current revision body, claim set/run references, upstream runs, review decisions, suggestions, dispositions, and audit events.
3. Validate every evidence `SourceSpan` against the immutable source. Derive snippets from storage. For invalid/missing spans, expose an `evidenceAvailability` state (`AVAILABLE`, `MISSING`, `INVALID`) and no offsets suitable for highlighting.
4. Map each upstream finding/failed component to one `ReviewFinding` using `REVIEW_SEVERITY-v1`; preserve upstream owner/ID/status/rule IDs verbatim. Map the actual Spec 006 policy keys, not Spec 007 severity labels, and mark unresolved source items as approval-blocking.

### Save/accept correction

1. Validate current `expectedRevision`, non-empty content, synthetic-reviewer label, and optional validated `SuggestedCorrection` reference. A raw Spec 006 suggestion is not an editable correction input.
2. In a write transaction, assert latest revision equals expected, append successor revision, append `NOTE_REVISION_CREATED`, and record the edit source (manual or accepted suggestion).
3. Project latest note as `AWAITING_FULL_VERIFICATION`. Do not mutate prior findings/runs; calculate their staleness from revision identity.
4. Return the successor. A failed expected-revision condition writes nothing and returns `409 STALE_REVISION`.

### Claim-level re-verification

1. Assert the target claim belongs to the exact current/reviewed immutable revision and source reference.
2. Invoke Spec 004 only for the specified current claim through the existing immutable-request contract; retain run references and feedback mapping.
3. Persist a `CLAIM_VERIFICATION` aggregate marked `NOT_APPROVAL_ELIGIBLE`. If it fails or has invalid evidence, retain a blocking review finding.

### Full-note verification

1. Read the exact latest revision in the transaction/snapshot used to create a `FullNoteVerification` request identity.
2. Run/retrieve a fresh Spec 003 extraction result through the in-process port for that revision. A failed result, or a valid `EMPTY` result, makes the aggregate invalid (`EMPTY_CLAIM_SET_REQUIRES_REVIEW` for the latter); it never silently reuses predecessor claims.
3. Invoke Spec 004 over the complete current claim set.
4. Invoke the Spec 005-owned `DeterministicValidationPort.run_for_revision` only with validated existing source facts and explicit alignments; preserve `NOT_EVALUABLE` outcomes. If required inputs/dependency are unavailable, record an invalid/failed component and block approval rather than synthesize alignments.
5. Invoke Spec 006 with its source-fact extraction run, exact claim set, source identity/hash/normalization, and optional linked 004/005 runs.
6. Validate that every success run binds to the identical source and note revision, has a valid terminal success shape, and contains expected coverage. A successful coverage run with unresolved source items is retained but marked not approval-eligible. Otherwise create `INVALID`/`FAILED` aggregate. Persist the component references and outcome append-only.
7. The valid aggregate can set latest-note projection to `IN_REVIEW` or `ELIGIBLE_FOR_APPROVAL` only after policy checks. It is never an approval.

No distributed transaction is introduced. Upstream immutable terminal run records can be created before the local aggregate commits; idempotency keys and aggregate request digest make retries safe. The aggregate is committed only when its complete terminal state is known. If a later edit wins, the completed aggregate remains historical and is naturally stale.

## Revision, approval, and concurrency strategy

Use positive integer revision sequence per `noteId` and a unique `(note_id, revision)` key. `expectedRevision` is compare-and-swap. The revision insert, latest-revision projection update, and audit append share one SQLite transaction.

Approval uses a single SQLite `BEGIN IMMEDIATE` (or repository equivalent transaction) to read the latest revision and required aggregate, apply all eligibility predicates, insert one `NoteDisposition(APPROVED)`, and append one audit event. The transaction has a uniqueness constraint permitting at most one approval disposition for `(note_id, revision)`. A concurrently appended revision forces `STALE_REVISION` or an eligibility conflict; an approval never targets an old revision by accident.

There is no attempt to lock human editing while verification runs. Immutable runs are allowed to finish after an edit, but cannot be considered current because their bound `noteRevision` differs from latest.

## Persistent storage strategy

New review-owned tables/records are append-only logical history; upstream records remain their owners' tables/repositories. The review repository initializes its local SQLite schema idempotently with `CREATE TABLE IF NOT EXISTS`; no migration framework is introduced.

| Record | Key / purpose |
| --- | --- |
| `review_note_revision_link` | `(note_id, revision)` → immutable source and predecessor references, latest projection metadata. It references existing Spec 002 revision identity rather than copying editable history. |
| `review_finding` | Stable `review_finding_id`, upstream owner/id or operational component failure, exact note/source identity, severity policy/version, display validation result. |
| `review_decision` | Immutable decision event, finding/revision reference, reviewer label, rationale, result. |
| `suggested_correction` | Immutable suggestion text, source spans/support validation state, source finding reference, acceptance/rejection event references. |
| `full_note_verification` | Aggregate identifier/digest, exact note/source/claim set, upstream component run IDs and per-component status. |
| `note_disposition` | Immutable approval/rejection record bound to one revision and full verification when approved. |
| `audit_event` | Append-only ordered actor/action/target/references/payload-digest record; full source/note bodies are not duplicated into telemetry. |

SQLite constraints: unique revision identity; unique upstream finding reference per immutable upstream run; foreign keys to known note/source/review records; immutable insert-only repository methods; decision/disposition audit events written in the same transaction; and unique approval per revision.

## Error handling and privacy

Use the existing project error convention: a typed JSON body with required `code` and `message`, plus context-specific `field`, `path`, and/or `correlationId` only when documented. Proposed review codes include `REVIEW_NOT_FOUND`, `NOTE_NOT_FOUND`, `FINDING_NOT_FOUND`, `STALE_REVISION`, `SOURCE_VERSION_MISMATCH`, `INVALID_EVIDENCE_REFERENCE`, `SUGGESTION_UNUSABLE`, `VERIFICATION_NOT_READY`, `VERIFICATION_INVALID`, `APPROVAL_PRECONDITION_FAILED`, `IDEMPOTENCY_KEY_CONFLICT`, and `DEPENDENCY_UNAVAILABLE`.

Errors never expose a partial approval or silently coerce invalid evidence. Logs/metrics retain IDs, policy/ruleset versions, statuses, counts, timings, retry/rejection codes, and correlation IDs, but no full source, note, prompt, or unvalidated model output. All fixtures and manual test data remain synthetic German only.

## Frontend plan

The React review screen has one source of truth: `ReviewContext` for a specific note/revision. It renders source and candidate note side by side; finding list/details; status/decision panel; suggestion controls; verification controls; approval/rejection actions; and audit timeline.

Highlight renderer inputs are typed spans with explicit coordinate system. Candidate claim spans use the Spec 003 note span fields; source evidence uses validated Spec 001 code-point spans. The client converts to UTF-16 only after server validation and verifies the supplied excerpt/identifier; ambiguous conversion or invalid span falls back to a labelled no-highlight state. Every selected finding has accessible textual claim/evidence references and severity text, not colour alone.

## Test strategy

| Level | Coverage |
| --- | --- |
| Unit | Severity mapping, state projection, suggestion support check, approval predicates, stale logic, audit event construction, and Unicode display conversion. |
| Contract | Pydantic/OpenAPI schemas, enums/version fields, required rationales, immutable identity references, common error body, and conditional approved/full-run constraints. |
| Repository | SQLite append-only behaviour, revision conflict, constraints, atomic approval, historical retrieval, and idempotency binding. |
| Service/integration | Ports/adapters for Specs 001–006; invalid/missing evidence, failed/malformed upstream runs, exact provenance, no algorithm duplication, and concurrent edit/approval race. |
| UI | Finding selection/evidence availability states, non-colour severity cue, suggestion acceptance, stale feedback, disabled/misleading-action prevention, and audit timeline. |
| Acceptance | HR-001 through HR-018 against synthetic German fixtures, including direct API bypass attempts and unresolved-source-item approval blocking. |
| Regression | Existing source/note/claim/004/005/006 contract/API suites plus full configured test suite, compile check, and `git diff --check`. |

## Engineering trade-offs

| Decision | Why | Cost / mitigation |
| --- | --- | --- |
| Append-only events plus immutable revisions | Meets provenance/audit requirements and makes stale results explicit. | More records/read projection; use indexed read model, never destructive compaction in PoC. |
| Synchronous orchestration consistent with Spec 004 | Avoids adding queues/jobs/microservices outside PoC scope. | May be slow; accurate pending/failure UI and bounded upstream retry behaviour required. |
| Aggregate full-note verification rather than a new verifier | Preserves ownership of 004/005/006 algorithms. | Needs adapters and exact provenance validation. |
| SQLite transaction for approval | Smallest reliable atomic guard in local PoC. | Single-writer contention acceptable; tests cover conflict. |
| Conservative unknown severity | Prevents silent downgrade when upstream contracts evolve. | Requires deliberate policy update for new finding types. |

## Constitution compliance check

| Principle | Planned control | Status |
| --- | --- | --- |
| Evidence fidelity | Immutable source/version binding, derived excerpts, invalid-span fail-closed display, source never equals candidate evidence. | Pass by plan |
| Human authority and fail-safe review | Explicit human decisions only; no auto-correct/approve; critical/open and failure guards; rejection available. | Pass by plan |
| Specification-first | Requirements, clarification, plan, data model, contracts, checklist, tasks, and analysis precede code. | Pass by plan |
| Contract-first modularity | Pydantic/OpenAPI review boundary and ports to 001–006; no verification algorithm copied. | Conditional on unresolved adapter gaps |
| Evaluation rigor | Synthetic acceptance fixtures, direct-bypass regression, clear test levels; no clinical-safety claim. | Pass by plan |
| Privacy/provenance/audit | Synthetic-only, reviewer labels, append-only revisions/events, content-minimized logs. | Pass by plan |
| Observable degradation | Explicit failed/invalid component state, status separation, idempotency, typed errors, no hidden success. | Pass by plan |

## External dependency gates

The concrete Specs 001–006 ports, repositories, endpoint contracts, and the Spec 008
evaluation package are external dependencies. Their presence and versions are not established
by the available planning archive. T001–T002 must produce the compatibility report before
implementation; no adapter, timeout, retry budget, migration behavior, or error contract may
be inferred. Any inherited operational limits must be copied from the verified upstream
contract, and missing limits must be versioned before the dependent service is enabled.

Spec 007 contributes feature acceptance fixtures but does not replace the constitutionally
required Spec 008 benchmark of at least 100 synthetic German scenarios, held-out measurements,
and release thresholds. No improvement or clinical-safety claim may be made without that
evaluation gate.

The cross-component review boundary, atomic approval transaction, and append-only audit
persistence are captured in [ADR 006](../../docs/adr/006-human-review-and-audit-boundary.md).

## Complexity justification

The full-note aggregate, atomic approval transaction, and append-only audit model are necessary complexity because the constitution requires final approval to bind a specific revision and validation run, and because cross-component results may otherwise become stale between UI display and approval. No asynchronous infrastructure, identity system, medical rules, or duplicate verifier is introduced.
