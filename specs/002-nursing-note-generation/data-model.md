# Data Model: Nursing Note Generation

## SourceDocument (Spec 001 dependency)

| Field | Required | Meaning |
| --- | --- | --- |
| `sourceId` | Yes | Stable source-document identifier. |
| `sourceVersion` | Yes | Exact immutable version used as evidence. |
| `language` | Yes | Must be German for generation. |
| `content` | Yes | Transcript content resolved by Spec 001. |

## NoteRevision

| Field | Required | Constraints |
| --- | --- | --- |
| `noteId` | Yes | Stable logical-note identifier. |
| `revision` | Yes | Positive integer, unique within `noteId`. |
| `previousRevisionId` | No | Links to immutable predecessor. |
| `content` | Yes | Editable note body. |
| `status` | Yes | Initial value exactly `DRAFT`; this feature writes no verified/approved status. |
| `origin` | Yes | `GENERATED` or `IMPORTED`. |
| `sourceId` | Yes | Foreign reference to the evidence `SourceDocument`; never null. |
| `sourceVersion` | Yes | Exact evidence version; never null. |
| `externalOrigin` | Import only | `{ system, externalNoteId }`; identifies candidate provenance and is distinct from evidence source. |
| `generationRunId` | Generated only | Provider/run audit identifier; no hidden reasoning. |
| `validationRunId` | Yes | Idempotent validation-run identifier. |
| `sourceTextHash` | Yes | Hash of immutable source bytes/text used by the run. |
| `normalizationPolicy` | Yes | Versioned policy defining source offsets and permitted exact normalization. |
| `modelId`, `promptVersion`, `schemaVersion`, `rulesetVersion` | Generated only | Versioned execution provenance. |
| `createdAt`, `createdBy` | Yes | Audit metadata. |

Constraint: `externalOrigin` is required when `origin=IMPORTED` and absent when `origin=GENERATED`. The pair `(noteId, revision)` is unique. A revision and all its facts are committed atomically.

## NursingFact

| Field | Required | Meaning |
| --- | --- | --- |
| `factId`, `noteId`, `revision` | Yes | Fact identity and exact parent revision. |
| `type` | Yes | `OBSERVATION`, `SYMPTOM`, `MEASUREMENT`, or `ACTION`. |
| `statement` | Yes | Readable statement; no added clinical meaning. |
| `residentSubject` | Yes | Resident identifier or explicit `UNKNOWN`. |
| `sourceAnchor` | Yes | Offset/range into the exact evidence source version, or declared external provenance for supplied facts. |
| `polarity` | When applicable | `AFFIRMED` or `NEGATED`. |
| `certainty` | When applicable | `CERTAIN`, `UNCERTAIN`, or source-equivalent qualifier. |
| `attribution` | When stated | Such as `RESIDENT_REPORTED` or `CAREGIVER_OBSERVED`. |
| `temporalQualifier` | When stated | Time/date/relative-time qualifier from source. |
| `numericValue`, `unit` | Together when stated | Strings preserving the source representation. |
| `provenance` | Yes | `GENERATED_FROM_SOURCE` or `EXTERNALLY_SUPPLIED`. |

Externally supplied facts may use a declared external anchor/provenance but are never represented as model-extracted facts. A declared external anchor contains both `externalSystem` and `externalFactId`; partial external provenance is invalid. Missing fields remain null/absent rather than inferred. Every cited source anchor must match the stored source text under `normalizationPolicy`; invalid offsets are rejected.
