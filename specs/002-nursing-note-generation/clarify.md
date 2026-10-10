# Clarifications: Nursing Note Generation

**Feature ID:** 002-nursing-note-generation  
**Status:** Resolved from supplied scope; no blocking question remains for specification.

This record resolves only ambiguities needed to make the feature testable. It does not expand the feature into clinical verification or approval.

| Area | Resolution | Effect on requirements |
| --- | --- | --- |
| Initial status | Every generated and imported note begins as `DRAFT`. | A successful request can never imply verification or approval. |
| Editable behavior | The returned/stored note body is editable after creation. An edit creates a new revision rather than overwriting traceability. | Revision lineage is mandatory. |
| External import | Import receives an already written candidate note plus declared origin/provenance. A source transcript is optional for import and does not trigger generation. | `POST /import` must not call the LLM; facts are not fabricated from the imported prose. |
| Structured facts on import | Imported notes may carry externally supplied facts, but the component must not claim generated/extracted facts where none were supplied. | Imported facts preserve their stated provenance. |
| Fact fidelity | A fact stores the textual/semantic source anchor as well as value, unit, polarity, certainty, and attribution where present. | Regression assertions can compare source meaning rather than merely note fluency. |
| Conflicting source statements | Preserve each source statement as distinct; do not reconcile, choose, or silently remove one. | Source anchors and fact identifiers are required per statement. |
| Missing detail | Missing values, units, actors, times, and clinical context remain missing. | No placeholders that look like source facts; no inference. |
| Provider failures | Invalid, incomplete, or schema-invalid generated output is a controlled failure. | No draft is persisted as successful unless required output validates. |
| Clinical language | Professional wording may improve readability but cannot introduce diagnoses or treatment advice. | Unsupported diagnostic inference is a negative regression case. |
| Downstream hand-off | This feature exposes a draft and provenance to later verification. | Claim classification, evidence assessment, approval, and dashboards remain out of scope. |

## Assumptions intentionally deferred

- Authentication, authorization, retention periods, and transport security are platform-wide concerns unless the project constitution or existing architecture assigns them here.
- The exact managed vocabulary for uncertainty and attribution may be finalized in implementation, provided it can losslessly retain the source wording and supports the scenarios in `spec.md`.
- The exact user-interface location for editing is not prescribed; the API contract guarantees editable draft content.
