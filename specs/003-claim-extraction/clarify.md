# Clarification Decisions — Spec 003

These decisions remove planning ambiguity. They are requirements decisions, not implementation choices.

| Topic | Decision | Reason |
|---|---|---|
| What is a claim? | A factual assertion in the candidate note that could be checked independently against a source. | Supports FR-06 without classifying evidence. |
| Atomicity | Split coordinated or compound assertions only where each resulting assertion has independent factual meaning; preserve shared context through spans/attributes. | Avoids both missed facts and meaningless grammatical fragments. |
| Overlap | Claim spans may overlap. A parent phrase may support several claims, each with a separate id. | UI and verification need addressability without forced text duplication. |
| Source of truth | The immutable stored note body identified by `noteRevisionId` is authoritative. | Prevents a client-supplied changed body from being associated with prior claims. |
| Revision policy | Any edited note is a new revision and must be extracted again before downstream re-verification. | Implements FR-21/FR-22 boundary. |
| Resident association | Carry the one required synthetic `residentTestId` from immutable note/source metadata. Do not infer, identify, or disambiguate residents; fail when the association is missing. | Matches the single-resident PoC boundary. |
| Offset convention | Persist zero-based end-exclusive Unicode-code-point offsets plus exact UTF-16 offsets for editor interoperability. | Makes server validation and browser highlighting unambiguous. |
| Stored text policy | Store synthetic note bodies as immutable UTF-8 text without post-storage normalization; validate each declared span against that exact body. | Makes provenance and location integrity testable. |
| Numeric representation | Preserve `raw` literally; store normalized decimal text only for a direct German comma-to-dot representation. | Prevents rounding and semantic changes. |
| Numeric typing | Use Pydantic `Decimal` internally for directly normalized values/ranges and serialize it as a decimal string at JSON boundaries. | Preserves precision while meeting typed-value requirements. |
| Units | Preserve literal unit text. Normalize only directly unambiguous units and never infer a missing unit. | Maintains numeric fidelity. |
| Negation | Model negation as a polarity plus the exact cue/span; do not treat missing information as negation. | Preserves scope and avoids hallucinated negatives. |
| Uncertainty | Record a certainty enum and exact cue/span. Uncertainty is not evidence weakness or contradiction. | Keeps linguistic stance separate from verification. |
| Attribution | Use resident/caregiver/third-party/document-author only when explicit; otherwise `UNSPECIFIED`. | Avoids converting a report into an observation. |
| Temporal context | Preserve only explicitly stated temporal language as raw text and span. | Avoids invented chronology. |
| Clinical conclusions | Extract them in `CLINICAL_CONCLUSION`; do not attach validity, diagnosis, or support status. | Downstream verification must assess them. |
| Medication | Preserve directly stated drug and administration details; do not infer indication, route, dose, frequency, or completion. | Medication statements are safety-sensitive. |
| Ambiguous text | Emit only claims safely grounded in text; omit speculative structured fields and add a warning if applicable. | Meaning preservation over forced completeness. |
| Malformed extraction output | Fail the entire result with no partial claims if JSON/schema/span validation fails. | Prevents a partial response from looking complete. |
| No assertions | Return a valid `EMPTY` result for text such as separators or greetings that contains no factual assertion. | Distinguishes no work from an extraction failure. |
| Endpoint exposure | A service interface is mandatory; the HTTP endpoint is optional and merely delegates to it. | Keeps extraction independently testable and deployable in a pipeline. |
| Identifier stability | Claim ids are unique within a revision/result. No stability across revisions is promised. | Edits may change boundaries and offsets. |
| Contract technology | Cross-component contracts are Pydantic models; any exposed HTTP contract is generated/tested through FastAPI OpenAPI. | Required by the constitution's engineering standards. |
| Run provenance | Every extraction attempt receives an idempotent `extractionRunId` and records provider/model/prompt/schema versions, input body hash, status, and timestamps in append-only logical history. | Keeps extraction attempts auditable without confusing them with verification runs. |
| Provider failures | Defined timeout, bounded retry, malformed-output, and unavailable-provider outcomes are typed failures with no partial claims. | Constitution requires observable, fail-safe degradation. |
| Data policy | Fixtures, requests, evaluations, logs, screenshots, and demos use synthetic data only. | Real patient/employee data is prohibited in the PoC. |
| Evaluation corpus | The feature contributes labeled extraction cases to the shared Spec 008 benchmark; held-out cases are not used for prompt tuning. | End-to-end benchmark ownership remains with Spec 008. |
| Verification handoff | Each successful/empty result carries immutable source-reference metadata and is retrievable by typed service/persisted result; Spec 004 must consume it before a revision can become verification-ready. | Preserves evidence-traceability without distributed delivery. |

## Resolved assumptions

1. The feature processes German-language note text; unsupported-language handling is an explicit failure, not translation or silent best-effort extraction.
2. A single claim can contain several numerical values when they belong to one inseparable assertion; independently verifiable measurements become separate claims.
3. Structured fields that cannot be reliably recovered are optional. `claimText` and `statementSpan` remain required for every emitted claim.
4. Warnings never upgrade incomplete extraction to success when a required schema or span invariant fails.
5. Candidate-note provenance in this feature is not source evidence. Spec 004 alone attaches source transcript evidence and assigns any supported/unsupported/contradicted/uncertain outcome.
6. An empty provider result is accepted only after a bounded independent factual-assertion safeguard; uncertain cases fail explicitly rather than becoming `EMPTY`.
