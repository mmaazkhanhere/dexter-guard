# Clarifications: Nursing Note Generation

**Feature ID:** 002-nursing-note-generation  
**Status:** Resolved for planning

| Area | Resolution |
| --- | --- |
| Evidence source | Every verification-ready generated or imported revision requires an existing `sourceId` and immutable `sourceVersion`. |
| Imported origin | `externalOrigin` records the source system/candidate identity only. It is distinct from, and cannot substitute for, the `SourceDocument` evidence reference. |
| Import facts | Import may accept externally supplied facts with external provenance, but it must not generate or infer facts from the note text. |
| Initial lifecycle | Every creation path returns `DRAFT`; neither path verifies or approves. |
| Edits | Editing creates a new revision with a predecessor link; prior revisions remain traceable. |
| Fidelity checks | Schema, source-anchor, field-preservation, and value/unit checks are limited generation-time guardrails. They do not establish semantic equivalence, clinical truth, or evidence verification. |
| Conflicts and omissions | Preserve conflicting statements separately. Missing source detail stays missing. |
| Failure | Invalid provider output or unresolvable source version creates no partial draft/fact success. |

The governing constitution is `.specify/memory/constitution.md`. No `.specify.memory` path is used.
