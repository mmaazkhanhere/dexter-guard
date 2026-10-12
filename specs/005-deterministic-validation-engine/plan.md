# Spec 005 — Technical Plan

**Input:** [spec.md](spec.md), [clarify.md](clarify.md), [data-model.md](data-model.md), [ADR 004](../../docs/adr/004-deterministic-validation-boundary.md), the constitution, and [architecture.md](../../docs/architecture.md)  
**Outcome:** A pure, versioned deterministic validation service and API contract for aligned structured facts and claims.

## Architecture and technology choices

Use the constitution's Python, FastAPI, Pydantic, SQLite local-PoC stack. The domain rule engine must be plain Python with `decimal.Decimal`; it takes typed domain objects and returns typed objects, without HTTP, database, network, clock, random, provider, or LLM dependencies. Pydantic validates API/repository boundaries. SQLite persistence is append-only behind the established repository abstraction. FastAPI only maps the published OpenAPI contract to the application service.

No new service, queue, model client, vector store, or clinical rules engine is introduced. Exact module/router/migration placement is discovered from existing application conventions before code changes (T001).

The cross-component boundary is fixed by [ADR 004](../../docs/adr/004-deterministic-validation-boundary.md): Spec 004 supplies semantic alignment only; Spec 005 never searches for a corresponding fact or determines semantic contradiction.

```text
Spec 001 immutable transcript ──┐
Spec 003 immutable claim ───────┼──> provenance + schema validators
Spec 004 preselected pairs ──────┘              │
                                                v
                                  pure deterministic rule engine
                                  ├─ structural / unit / numeric rules
                                  └─ independent evidence integrity rules
                                                │
                                                v
                                   immutable ValidationRun + API
                                      ├─ Spec 007 review rendering
                                      └─ Spec 008 rules/fixture evaluation
```

## Contract and data-flow design

1. Parse the reference-only `ValidationRequest` from the versioned OpenAPI/Pydantic schema. It binds the run to exact `noteId` and `noteRevision`; reject missing or malformed envelope identifiers as `422/SCHEMA_ERROR` and do not partially execute.
2. Resolve exact immutable source snapshot, facts, claims, and selected upstream alignment records. Never accept copied transcript text, source facts, or claims in an HTTP request as a substitute for stored upstream records.
3. Validate stable identities: unique submitted alignment IDs and unique evidence-reference IDs; source fact source identity equals run identity; every alignment references existing selected records and is one source-fact/claim comparison pair. A fact or claim MAY appear in several alignments and an unaligned selected record is outside the comparison scope.
4. For every source and claim evidence reference, independently apply `EVD-001`, `EVD-002`, and `EVD-003` using the canonical zero-based, start-inclusive/end-exclusive Unicode code-point convention.
5. Validate the requested note binding. A resolved claim with a missing/null revision yields `STR-002`; a non-null note ID/revision mismatch is `409/PROVENANCE_CONFLICT` and returns no run. For each selected alignment in input order, validate prerequisites. `UNAVAILABLE`, `AMBIGUOUS`, and `REJECTED` yield traceable `ALIGN-001` `NOT_EVALUABLE` findings; invalid unit/category fields yield structural results before any numeric conversion. Reject an unsupported category while resolving an immutable referenced record, before rule execution.
6. Convert permitted scalar values exactly with `Decimal`; compare canonical values. Compare typed blood pressure components exactly. Evaluate explicit approximation separately.
7. Collect only `FAIL` and `NOT_EVALUABLE` records for reviewer response by default. Keep optional internal/pass trace for debugging and fixture assertions.
8. Sort by declared input alignment order and catalog rule order. Persist and return the immutable result with source identity, requested note ID/revision, `DVE-CONTRACT-v1`, `DVE-RULESET-v1`, canonical input digest, and deterministic engine version.

### Rule precedence

| Condition | Required behavior |
| --- | --- |
| Envelope invalid | `422/SCHEMA_ERROR`; no run. |
| Missing source/fact/claim/alignment record | `404/*_NOT_FOUND`; no run. |
| Resolved record conflicts with requested source/note/alignment provenance | `409/PROVENANCE_CONFLICT`; no run. |
| Repository/storage unavailable | `503/DEPENDENCY_UNAVAILABLE`; no run. |
| Unexpected failure | `500/INTERNAL_ERROR`; no run. |
| Evidence reference invalid | Emit its EVD failure, independent of numeric eligibility. |
| Alignment `UNAVAILABLE`/`AMBIGUOUS`/`REJECTED` | `ALIGN-001` `NOT_EVALUABLE`; no NUM mismatch. |
| Unknown, duplicated, or internally inconsistent submitted alignment reference | `404/*_NOT_FOUND` or `409/PROVENANCE_CONFLICT`; no run. |
| Invalid type / missing note revision / invalid category-unit pairing | Emit STR failure and skip dependent NUM rules. |
| Unit dimensions incompatible | Emit NUM-003 and skip NUM-001. |
| Compatible scalar values differ | Emit NUM-001. |
| Structured approximation unknown | NUM-004 is `NOT_EVALUABLE`; scalar comparison may still occur. |

No precedence transforms an objective failure into a semantic status, a successful result, or an approval decision.

## Internal interfaces

```text
ValidationService.execute(request) -> ValidationRun | ApiError
SourceSnapshotRepository.get(source_id, source_version) -> TranscriptSnapshot
FactRepository.get_many(ids) -> immutable SourceFact records
ClaimRepository.get_many(ids) -> immutable Claim records
ValidationRunRepository.append(run) -> immutable ValidationRun
RuleEngine.evaluate(snapshot, facts, claims, alignments, ruleset) -> ordered RuleResult[]
EvidenceValidator.validate(snapshot, reference) -> RuleResult[]
UnitNormalizer.normalize(measurement) -> CanonicalMeasurement | RuleResult
```

The service passes resolved immutable records to `RuleEngine`; it does not give a rule access to semantic-verifier clients or mutable upstream objects. All `Decimal` string serialization is canonical (no locale formatting) in persisted expected/observed values. German comma parsing is input parsing only.

## Persistence, traceability, and API

Create an immutable `ValidationRun` record associated with exact source ID/version, requested note ID/revision, resolved source fact and claim IDs, alignment IDs/statuses, evidence-reference IDs, contract/ruleset/engine versions, canonical input digest, and ordered findings. The public response returns all of that binding data. `ValidationFinding.evidenceReferenceIds`, `expectedValue`, `observedValue`, and `unit` are always present; conditional non-null/reference requirements follow DVE-011. The repository uses a unique run ID and, when an idempotency key is introduced by existing API convention, atomically binds it to the canonical input digest. A later re-run may be represented separately only under that application's established run policy; it must have identical normalized findings for identical inputs/rules.

Expose `POST /api/v1/deterministic-validation-runs` using [the contract](contracts/deterministic-validation.openapi.yaml). The public response does not include a full transcript and only includes source-derived evidence text required by review. It contains no approval state. A later endpoint or review state change requires a new specification.

Spec 005 has no external severity field. Spec 007 maps the rule result to the project severity vocabulary (`minor`, `major`, `critical`) and applies approval policy without changing the rule outcome.

## Test strategy

| Level | Coverage |
| --- | --- |
| Unit | Decimal parsing/conversion; scalar and BP value shapes; category-unit matrix; numeric/BP/precision rules; deterministic ordering; no LLM port/import. |
| Property/boundary | Equivalent conversions; decimal edge values; invalid combinations; zero/negative/reversed/end-boundary Unicode spans; repeated execution equality. |
| Contract | OpenAPI/Pydantic closure; unknown fields; resolved-record category validation; requested note binding; finding conditional fields; `ApiError` codes; version constants. |
| Integration | Immutable source lookup; wrong-note provenance conflict; unavailable storage; run append/replay with complete revision/digest/engine metadata; source-fact/claim/alignment integrity; API mapping. |
| Acceptance | AT-001 through AT-021 using versioned synthetic German fixtures, exact rule/outcome/reference and API-error assertions. |
| Consumer handoff | Spec 007 rendering fixture and Spec 008 rule/fixture manifest. |

Tests must monkeypatch/block network and model-provider adapters; no rule outcome may require an LLM fixture. Use only synthetic German nursing-documentation data.

## Constitution check

| Principle | Plan control | Status |
| --- | --- | --- |
| Evidence fidelity | Exact immutable source/version/spans, Decimal conversions, no invented alignment. | Pass |
| Human authority | `requires_review` only; no correction or approval logic. | Pass |
| Specification first | Versioned requirements, contracts, rule catalog, tests, and tasks exist before code. | Pass |
| Contract-first / deterministic | Pydantic/OpenAPI boundaries and pure rule engine, documented conversions. | Pass |
| Evaluation rigor | Synthetic acceptance fixtures and Spec 008 manifest handoff. | Pass |
| Privacy/provenance | Synthetic-only fixtures, immutable identities, minimized response excerpts. | Pass |
| Observable degradation | Schema errors and not-evaluable outcomes explicit; no false pass. | Pass |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Upstream semantic alignment unavailable or ambiguous | Require an explicit non-`ALIGNED` comparison pair and emit `ALIGN-001` `NOT_EVALUABLE`; duplicated source facts/claims across pairs remain valid; never semantic-match locally. |
| Locale or float conversion error | Restrict parser; use exact Decimal conversion and property tests. |
| Spec 004/005 findings conflict | Preserve both finding sets; leave policy resolution to Spec 007. |
| Stale copied source evidence | Resolve exact version and compare quotation substring before accepting it. |
