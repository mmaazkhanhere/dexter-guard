# Spec 006 - Technical Plan

**Input:** [spec.md](spec.md), [clarify.md](clarify.md), [data-model.md](data-model.md), [contracts/coverage-runs.openapi.yaml](contracts/coverage-runs.openapi.yaml), constitution, and [architecture.md](../../docs/architecture.md).  
**Outcome:** A source-to-note coverage service that produces immutable, source-grounded, reviewer-facing completeness assessments without editing notes or making approval/severity decisions.

## Architecture and technology choices

Use the established Python 3.11+, FastAPI, Pydantic v2, pytest, and local immutable repository conventions. Add an isolated `source_coverage` package and route integration using the existing source/note/claim patterns. Pydantic models validate transport, repository, semantic-provider, and persistence boundaries. Plain Python deterministic code validates provenance, source spans, source hash/normalization integrity, result closure, status/attribute invariants, policy lookup, result ordering, source-derived quotations, metrics, and run immutability. The cross-component boundary is documented in [ADR 005](../../docs/adr/005-source-coverage-boundary.md).

A pluggable source-fact extractor and semantic matcher are ports. Their structured output remains untrusted until validated. They may use an approved provider for German semantic extraction/equivalence; deterministic code must not replace semantic equivalence with a keyword heuristic or infer clinical facts. No vector store, new queue, clinical rules engine, autonomous writer, or severity engine is introduced.

```text
Spec 001 immutable source snapshot ----+--> source-fact extraction port
                                        |       | structured candidates
Spec 002 immutable note revision -------+       v
                                                source-fact validator/store
Spec 003 claim extraction run ----------+               |
                                                        v
Spec 004/005 immutable findings ----> coverage service / matcher port
                                             |      | semantic relations
                                             v      v
                                     deterministic integrity/policy layer
                                             |
                                             v
                             immutable CoverageRun + FastAPI response
                                     |                      |
                                     v                      v
                           Spec 007 review policy       Spec 008 benchmark
```

## Component responsibilities

| Component | Responsibility | Must not do |
| --- | --- | --- |
| SourceFactExtractionService | Resolve a source snapshot, invoke structured extractor, validate/persist atomic facts and unresolved source items. | Treat a provider's uncited text as a fact; create clinical diagnoses. |
| CoveragePolicy | Assign `REQUIRED`/`IMPORTANT`/`CONTEXTUAL` and a Spec 007 policy key from documented fact category/attributes. | Assign final severity. |
| SemanticCoverageMatcher | Compare one resolved source fact with resolved note claims and return structured related/faithful/partial/distorted/unresolved relationships. | Modify claims/note or use unsupported source evidence. |
| CoverageService | Resolve immutable records, validate provenance, orchestrate matching, apply status precedence, derive quotes/findings/counts, persist run. | Re-run Spec 004/005 classifiers or approve a note. |
| Span validator | Resolve exact transcript and validate/derive source excerpts. | Accept normalised or provider-supplied quotation as authority. |
| Repositories | Preserve immutable source facts, unresolved items, runs, and related finding references. | Rewrite upstream source/note/claim records. |
| API adapter | Map published schema to service and stable error responses. | Accept source/note/fact prose as an authority. |

## Data flow

1. `SourceFactExtractionService.extract(sourceId, sourceVersion)` resolves the exact immutable Spec 001 transcript and writes an immutable extraction result containing `SourceFact` records and, only when needed, `UnresolvedSourceItem` records.
2. The service validates every source span using the canonical Unicode code-point convention and recomputes each source quotation. Invalid candidate output fails the extraction result; a structured unresolved item is valid only when it cites source span(s) and makes no asserted fact.
3. `POST /api/v1/coverage-runs` receives reference-only IDs: source snapshot, resident context, note ID/revision, source-fact extraction run, claim-set/extraction run, dataset/ruleset versions, and a required idempotency key. It resolves all records and validates resident/source/note binding, source text hash plus declared normalization policy, and source-fact policy versions.
4. The service loads the exact immutable Spec 003 claims and optional immutable Spec 004/005 finding references for correlation only. Spec 004/005 results never establish missing source facts.
5. For each expected source fact, the matcher compares that fact with the complete resolved claim set. It returns a schema-valid relation and listed material attributes. For source unresolved items it returns no semantic relation; the orchestrator emits `UNCERTAIN` without a fact.
6. The deterministic layer applies `COVERAGE_STATUS-v1` precedence, verifies all result closure rules, derives source quotes, filters contextual facts from denominator/findings, links overlap references, creates findings, and calculates labelled runtime counts.
7. The repository atomically appends an immutable `CoverageRun`. Every run records source/note/resident provenance, ruleset/dataset/provider/model/prompt versions, correlation ID, and idempotency key. A repeated idempotency key with the same canonical digest returns the original run; a different digest returns `409 IDEMPOTENCY_KEY_CONFLICT` without another attempt. A re-run against a revised note is a new run with the new exact revision/claim set; earlier runs remain unchanged.
8. FastAPI returns the terminal run. It exposes no approval state, no auto-apply operation, and no full transcript.

## Interfaces

```text
SourceFactExtractionService.extract(source_id, source_version)
  -> SourceFactExtractionRun | ExtractionFailure

SourceFactRepository.get_run(source_fact_extraction_run_id)
  -> immutable SourceFactExtractionRun

CoverageService.execute(CoverageRunRequest)
  -> CoverageRun | ApiError

SemanticCoverageMatcher.match(source_fact, claims, source_snapshot)
  -> MatcherResult  // one relation per evaluated source fact

SourceSpanResolver.resolve(snapshot, span)
  -> source-derived quote | IntegrityError

CoverageRunRepository.append(run)
  -> immutable CoverageRun
```

The source-fact extractor and matcher input/output schemas must include model, prompt, provider, dataset, ruleset, and schema versions. The coverage service stores those versions in the immutable run. Provider response handling has a 30-second timeout and at most 2 attempts per operation; retries reuse the same run ID and idempotency key and cannot duplicate reviewer actions. A timeout, malformed result, duplicate/missing relation, unknown claim ID, or unsupported status is a failed run, not an `UNCERTAIN` assessment.

## Matching and classification design

The matcher may surface only the following per-fact relation classes: `FAITHFUL`, `RELATED_ATTRIBUTE_OMITTED`, `RELATED_ATTRIBUTE_DISTORTED`, `NO_RELATED_CLAIM`, or `UNRESOLVED`. It must return referenced claim IDs and explicit material-attribute sets, never a prose-only judgment. The deterministic orchestrator maps them:

| Input | Coverage status |
| --- | --- |
| Source unresolved item | `UNCERTAIN` |
| Matcher `UNRESOLVED` | `UNCERTAIN` |
| One or more `FAITHFUL` relation | `COVERED` |
| No faithful relation; one or more distorted relation | `DISTORTED` |
| No faithful/distorted relation; one or more omitted-attribute relation | `PARTIALLY_COVERED` |
| Only `NO_RELATED_CLAIM` | `MISSING` |

This implements the canonical policy's practical precedence: a faithful independent representation wins for coverage, although distorted restatements remain linked separately. Numeric incompatibility must cite an existing matching Spec 005 finding when supplied; it does not perform decimal/unit calculation locally.

## Persistence, provenance, and revision behaviour

Use immutable, append-only records behind repository interfaces. Persist:

- source ID/version and transcript hash;
- exact note ID/revision and immutable claim-set ID;
- source-fact extraction run and each source-fact/unresolved-item ID;
- all matched claim IDs and related Spec 004/005 finding references;
- status/expectation policy, extractor/matcher/provider/prompt/schema versions;
- canonical request digest, required idempotency key, timestamps, correlation ID, execution status, and safe failure;
- ordered assessments, derived findings, and labelled runtime counts.

The request identity digest covers every immutable input reference, source hash/normalization policy, resident context, dataset/ruleset/policy versions, and provider/model/prompt configuration. Bind the required idempotency key atomically to this digest; the same key plus a different digest returns `409 IDEMPOTENCY_KEY_CONFLICT` and never starts another run. Never mutate a run to show that a later note revision addressed its finding.

## API and error policy

Implement `POST /api/v1/coverage-runs` according to the versioned OpenAPI contract. The endpoint must reject unknown fields and copied source/note/claim content. It returns `422 SCHEMA_ERROR` for syntactic invalidity, `404` for missing source/note/extraction records, `409 PROVENANCE_CONFLICT` for stale/cross-bound records, `503 DEPENDENCY_UNAVAILABLE` for repositories, and a terminal `FAILED` run or documented `500` response for execution/persistence/provider failures after request identity is established.

No failed response may contain a successful partial assessment, an approval signal, or an auto-corrected note.

## Test strategy

| Level | Coverage |
| --- | --- |
| Unit | Policy mapping, relation-to-status precedence, finding construction, denominator/counts, suggestions, source quote derivation, and no auto-edit/severity behaviour. |
| Contract | Pydantic/OpenAPI closure, reference-only request, source-fact/unresolved-item invariants, finding conditional fields, error codes, version fields, and source-span integrity. |
| Provider boundary | Valid/invalid structured extraction/matcher output; model timeout/retry; no-citation rejection; unresolved item non-invention. |
| Repository/integration | Immutable fact/run persistence, source/note/claim provenance, stale revision/cross-note rejection, historical re-evaluation, idempotency binding, and linked 004/005 findings. |
| Acceptance | COV-001 through COV-010 with synthetic German fixtures; exact status, attribute, source quote/span, link, and denominator assertions. |
| Property/boundary | Unicode code points including umlauts, combining characters, emoji and line endings; empty/reversed/out-of-range spans; duplicate IDs; exhaustive status closure/order; no zero-denominator 100%. |
| Evaluation handoff | Manifest including source text, manual expected facts, annotations, source spans, expected claim-level outcomes, materiality/severity labels, annotation provenance/dispute resolution, train/held-out split, dataset version, and raw-count metric schema for Spec 008. |

Tests block network except mocked provider ports. Deterministic validation/import tests prove source span, contract, policy, and persistence code does not invoke model/network dependencies.

## Observability and privacy

Emit structured, content-minimized telemetry and persist `executionMetrics` on every run: coverage run ID, source/note/resident version IDs, policy/ruleset/dataset/model/prompt versions, status counts, expected-fact count, runtime denominator, finding count, latency, retry count, input/output token counts, inference cost, error/rejection code, warning count, and linked finding counts. Spec 008 additionally reports critical-error recall, false-positive rate, claim classification performance, completeness, latency, inference cost, reviewer workload, omission recall, and false omission warning rate with stated denominators. Do not log full transcripts, notes, prompts, or uncited model output. Use synthetic data only.

## Constitution check

| Principle | Plan control | Status |
| --- | --- | --- |
| Evidence fidelity | Source-only facts, exact immutable spans, derived quotes, no fact without cited evidence. | Pass |
| Human authority | Findings require review; no write, approval, diagnosis, or severity decision. | Pass |
| Specification first | Versioned policy, models, OpenAPI, acceptance cases, tasks, and convergence procedure precede code. | Pass |
| Contract-first modularity | Pydantic/reference-only boundaries; semantic ports isolated from deterministic validation. | Pass |
| Evaluation rigor | Manual annotations and held-out metrics owned by Spec 008; raw counts required. | Pass |
| Privacy/provenance | Synthetic-only, immutable run binding, resident trust context, source hash/normalization, required idempotency, minimal telemetry. | Pass |
| Observable degradation | Provider/integrity/provenance failure is explicit; timeout/retry, token/cost, rejection, and warning telemetry cannot pass as coverage. | Pass |

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Extractor misses a fact, inflating runtime completeness | Distinguish runtime counts from Spec 008 manually annotated benchmark metrics; track extraction recall. |
| Semantic paraphrase triggers false omission | Use structured relation/attribute output and dedicated German paraphrase fixtures. |
| Qualifier loss hides documentation risk | Treat polarity, certainty, attribution, temporality, laterality, value/unit/approximation as material. |
| Provider makes uncited or malformed assertion | Validate spans/quotes/results deterministically; fail run or record only source-linked unresolved item. |
| Duplicate contradiction/omission alerts confuse reviewer | Preserve correlation IDs; Spec 007 renders/consolidates final review policy. |
| Note edits appear to resolve old findings | Bind every run to immutable note revision and never mutate history. |

