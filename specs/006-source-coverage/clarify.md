# Spec 006 - Clarification Record

**Purpose:** Resolve safety-, evidence-, and contract-affecting ambiguity before planning. Resolved decisions are folded into [spec.md](spec.md).  
**Status:** No blocking product ambiguity remains.

| ID | Question | Decision |
| --- | --- | --- |
| CL-001 | What is evaluated? | One atomic expected source fact at a time, plus explicit unresolved-source items. The service never turns an uncertain source passage into an asserted fact. |
| CL-002 | What establishes a source fact? | Only a non-empty valid span in the requested immutable transcript version. Note text, claims, retrieval, prior findings, and model memory cannot establish it. |
| CL-003 | Which source content is expected? | `COVERAGE_EXPECTATION-v1` labels a fact `REQUIRED`, `IMPORTANT`, or `CONTEXTUAL`. Only the first two are in the runtime completeness denominator. |
| CL-004 | Who assigns severity? | Spec 006 supplies a documented expectation and Spec 007 policy key only. Spec 007 owns final severity labels and approval effects. |
| CL-005 | How are offsets represented? | Unicode code points, zero-based, start-inclusive, end-exclusive, calculated from the exact stored source text. |
| CL-006 | Is exact string matching sufficient? | No. Semantic equivalence can cover a fact only when material attributes are faithful. |
| CL-007 | Which attributes are material? | At minimum: subject, polarity/negation, certainty, attribution, temporality, laterality, numeric value/unit/approximation, mobility assistance, and care action. The source-fact policy may add category-specific material attributes versionedly. |
| CL-008 | How are multiple related note claims handled? | A single faithful claim makes the fact `COVERED`; a separate distorted duplicate remains linked to Spec 004/005 but does not create an omission finding for an otherwise covered fact. |
| CL-009 | What is the status precedence? | Unresolved source/match -> `UNCERTAIN`; material meaning change -> `DISTORTED`; faithful match -> `COVERED`; related incomplete match -> `PARTIALLY_COVERED`; no related match -> `MISSING`. |
| CL-010 | What does source-extraction uncertainty mean? | Return an `UnresolvedSourceItem` with source evidence and explanation, no asserted fact values, an `UNCERTAIN` assessment, and no denominator entry. Infrastructure/provider malformation is a non-successful run, not `UNCERTAIN`. |
| CL-011 | How do numerical mismatches interact with Spec 005? | Spec 006 reports `DISTORTED` for coverage semantics and links the matching Spec 005 numeric/unit finding. Spec 005 remains the owner of deterministic numeric comparison. |
| CL-012 | How do contradictions interact with Spec 004? | The coverage service preserves `relatedFindingRefs` to applicable immutable Spec 004 `CONTRADICTED`/`UNCERTAIN` findings. It does not recalculate evidence support statuses. |
| CL-013 | What happens when claims/source facts cannot be fully resolved? | Missing, stale, cross-note/source, duplicate, invalid-span, or malformed provider records cause a typed non-successful run with no authoritative partial result. |
| CL-014 | Can suggestions change the draft? | Never. Suggestion text is a source-derived review aid. It cannot be applied, saved, approved, or presented as a confirmed clinical fact by this feature. |
| CL-015 | Which completeness value is authoritative for reporting? | Benchmark completeness uses manually annotated expected facts, not only system-extracted facts. Runtime counts are clearly labeled extracted-fact counts. |
| CL-016 | What creates a re-evaluation? | An immutable new note revision and its claim-set extraction run. Prior coverage runs/findings are retained and never marked resolved automatically. |
| CL-017 | Which run metadata is mandatory? | Every run records resident context, source text hash, normalization policy, ruleset version, dataset version, provider/model/prompt versions (nullable only before invocation), correlation ID, and a required idempotency key. |
| CL-018 | How are retries made safe? | Each provider operation has a 30-second timeout and at most two attempts. Retries reuse the same run ID and idempotency key; a different request digest with the same key is a conflict. |

## Canonical examples

| Source | Candidate note | Required outcome |
| --- | --- | --- |
| `Frau Müller klagte über Schmerzen im linken Knie.` | `Bewohnerin berichtet über linksseitige Knieschmerzen.` | `COVERED` if subject/attribution resolve faithfully. |
| `Schmerzen im linken Knie.` | `Knieschmerzen.` | `PARTIALLY_COVERED`, missing `laterality`. |
| `Bewohnerin verneint Schwindel.` | no related claim | `MISSING`, preserving `NEGATED` polarity. |
| `Bewohnerin wirkte möglicherweise müde.` | `Bewohnerin war müde.` | `DISTORTED`, distorted `certainty`. |
| `Temperatur ca. 37,8 °C um 08:00 Uhr.` | `Temperatur 37,8 °C.` | `PARTIALLY_COVERED`, missing `approximation` and `temporal`. |
| Ambiguous source syntax with a cited clause that cannot be separated safely. | any note | `UNCERTAIN` unresolved item; no invented source fact or denominator entry. |

## Deferred non-behavioural decisions

- Exact approved model provider and prompt implementation. The timeout and bounded retry count are fixed by CL-018.
- Repository/SQLite migration mechanics and FastAPI router registration, following existing project conventions.
- Spec 007's final severity mapping and approval policy.
- Spec 008 release thresholds and benchmark split implementation.

