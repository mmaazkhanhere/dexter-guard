# Data Model: Source Transcript Ingestion and Evidence Reference Foundation

This is the canonical Spec Kit-named data-model artifact. It defines the same model described in `data_model.md`; new implementation and task-generation tooling should use this hyphenated path.

## SourceDocument

One immutable version of one German text transcript for one synthetic resident.

| Field | Type | Required | Constraint |
| --- | --- | --- | --- |
| `source_id` | string | yes | Globally unique logical source identifier. |
| `source_version` | positive integer | yes | Starts at `1`; unique within `source_id`. |
| `resident_test_id` | scalar string | yes | Exactly one structured synthetic-resident identifier; no resident inference. |
| `language` | enum | yes | `de-DE`. |
| `transcript_text` | string | yes | Non-blank exact original text; no Unicode or line-ending normalization. |
| `created_at` | timestamp | yes | Creation time of this immutable version. |

The composite identity is `(source_id, source_version)`. Initial submission creates a new source at version `1`; revision creates the next version without modifying previous records.

## SourceSpan

A reusable evidence reference to an exact range in one immutable source version.

| Field | Type | Required | Constraint |
| --- | --- | --- | --- |
| `source_id` | string | yes | Existing source identifier. |
| `source_version` | positive integer | yes | Existing version of that source. |
| `start` | non-negative integer | yes | Inclusive zero-based Unicode scalar-value/code-point index. |
| `end` | positive integer | yes | Exclusive zero-based Unicode scalar-value/code-point index. |

Valid spans satisfy:

```text
0 <= start < end <= unicode_scalar_value_length(transcript_text)
```

Offsets count Unicode scalar values/code points, not UTF-8 bytes, UTF-16 code units, or grapheme clusters. The stored text is not normalized before indexing. CRLF counts as two scalar values; LF counts as one. A span may split a grapheme cluster.

## Persistence invariants

- The unique persistence key is `(source_id, source_version)`.
- Source text is stored exactly as accepted.
- Source versions are immutable and historical versions remain retrievable.
- Version creation atomically checks `expected_source_version` and inserts the next version.
- A stale expected version or concurrent uniqueness race returns `VERSION_CONFLICT` and creates no partial record.
- `resident_test_id` and `language` are inherited during revision and cannot be changed by revision input.

## Structured input invariant

The API enforces exactly one scalar `resident_test_id` field. It rejects missing, blank, repeated, array-valued, or schema-invalid identifiers. It does not inspect transcript meaning, disambiguate residents, or call an LLM.

## Downstream references

`NursingNote`, `SourceFact`, `Claim`, `EvidenceFinding`, `ReviewDecision`, and `EvaluationCase` may reference this model. They must retain `source_id` and `source_version`; copied excerpts are derived views, not authoritative source data.

## Contract source

The normative API representation is `specs/001-source-and-note-ingestion/contracts/source-api.yaml`.
