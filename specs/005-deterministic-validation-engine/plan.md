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
Spec 004 alignment (optional) ──┘              │
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

1. Parse the reference-only `ValidationRequest` from the versioned OpenAPI/Pydantic schema. Reject missing or malformed envelope identifiers as `SCHEMA_ERROR`; do not partially execute.
2. Resolve exact immutable source snapshot, facts, claims, and optional upstream alignment records. Never accept copied transcript text, source facts, or claims in an HTTP request as a substitute for stored upstream records.
3. Validate stable identities: unique fact, claim, alignment, and evidence-reference IDs; source fact source identity equals run identity; claim has note revision; every selected fact and claim appears in exactly one selected alignment; and every alignment references existing selected records.
4. For every source and claim evidence reference, independently apply `EVD-001`, `EVD-002`, and `EVD-003` using the canonical zero-based, start-inclusive/end-exclusive Unicode code-point convention.
5. For each alignment in input order, validate prerequisites. `UNAVAILABLE`, `AMBIGUOUS`, and `REJECTED` yield traceable `ALIGN-001` `NOT_EVALUABLE` findings; invalid unit/category fields yield structural results before any numeric conversion. Reject an unsupported category while resolving an immutable referenced record, before rule execution.
6. Convert permitted scalar values exactly with `Decimal`; compare canonical values. Compare typed blood pressure components exactly. Evaluate explicit approximation separately.
7. Collect only `FAIL` and `NOT_EVALUABLE` records for reviewer response by default. Keep optional internal/pass trace for debugging and fixture assertions.
8. Sort by declared input alignment order and catalog rule order. Persist the immutable result with `DVE-CONTRACT-v1`, `DVE-RULESET-v1`, input digest, and deterministic engine version; return the persisted representation.

### Rule precedence

| Condition | Required behavior |
| --- | --- |
| Envelope invalid | Reject with `SCHEMA_ERROR`; no run. |
| Evidence reference invalid | Emit its EVD failure, independent of numeric eligibility. |
| Alignment `UNAVAILABLE`/`AMBIGUOUS`/`REJECTED` | `ALIGN-001` `NOT_EVALUABLE`; no NUM mismatch. |
| Required alignment record missing or duplicated | Reject as `SCHEMA_ERROR`/provenance-invalid; no empty successful run. |
| Invalid type / missing note revision / invalid category-unit pairing | Emit STR failure and skip dependent NUM rules. |
| Unit dimensions incompatible | Emit NUM-003 and skip NUM-001. |
| Compatible scalar values differ | Emit NUM-001. |
| Structured approximation unknown | NUM-004 is `NOT_EVALUABLE`; scalar comparison may still occur. |

No precedence transforms an objective failure into a semantic status, a successful result, or an approval decision.

## Internal interfaces

```text
ValidationService.execute(request) -> ValidationRun | SchemaError
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

Create an immutable `ValidationRun` record associated with exact source ID/version, resolved source fact and claim IDs, note ID/revision, alignment IDs/statuses, evidence-reference IDs, contract/ruleset/engine versions, canonical input digest, and ordered findings. `ValidationFinding.evidenceReferenceIds` is always an array; it is empty only where the rule has no relevant evidence reference. The repository uses a unique run ID and, when an idempotency key is introduced by existing API convention, atomically binds it to the canonical input digest. A later re-run may be represented separately only under that application's established run policy; it must have identical normalized findings for identical inputs/rules.

Expose `POST /api/v1/deterministic-validation-runs` using [the contract](contracts/deterministic-validation.openapi.yaml). The public response does not include a full transcript and only includes source-derived evidence text required by review. It contains no approval state. A later endpoint or review state change requires a new specification.

Default severity hints for v1 fixtures: structural and evidence-integrity failures `HIGH`; numeric, incompatible-unit, precision, and BP mismatches `HIGH`; not-evaluable outcomes `MEDIUM`. This is an implementation-neutral default only—Spec 007 can map a finding to final policy severity without changing its rule outcome.

## Test strategy

| Level | Coverage |
| --- | --- |
| Unit | Decimal parsing/conversion; scalar and BP value shapes; category-unit matrix; numeric/BP/precision rules; deterministic ordering; no LLM port/import. |
| Property/boundary | Equivalent conversions; decimal edge values; invalid combinations; zero/negative/reversed/end-boundary Unicode spans; repeated execution equality. |
| Contract | OpenAPI/Pydantic closure; unknown fields; resolved-record category validation; required IDs/revisions/alignment coverage/evidence-reference IDs; finding shape and nullable values; version constants. |
| Integration | Immutable source lookup; outdated versions; run append/replay; source-fact/claim/alignment integrity; API mapping. |
| Acceptance | AT-001 through AT-016 using versioned synthetic German fixtures, exact rule/outcome/reference assertions. |
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
| Upstream semantic alignment unavailable or ambiguous | Require an explicit non-`ALIGNED` record and emit `ALIGN-001` `NOT_EVALUABLE`; reject a missing required record; never semantic-match locally. |
| Locale or float conversion error | Restrict parser; use exact Decimal conversion and property tests. |
| Spec 004/005 findings conflict | Preserve both finding sets; leave policy resolution to Spec 007. |
| Stale copied source evidence | Resolve exact version and compare quotation substring before accepting it. |
