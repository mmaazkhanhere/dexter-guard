# Spec 007 Clarifications

**Method:** Requirements clarification completed from the authoritative constitution and established contracts before technical planning. This is not an implementation decision record.

| Question | Resolution | Basis / impact |
| --- | --- | --- |
| Can a human adjudication clear a critical contradiction? | No. A critical finding requires correction and a subsequent valid full-note verification that no longer produces the blocker. | Constitution II; FR-23; prevents a rationale from overriding evidence integrity. |
| What makes a finding stale? | A finding is stale for approval when tied to any predecessor note revision. It remains in history. | Specs 002–006 immutable revision/run semantics; FR-19, FR-25. |
| May a successful claim-level run authorize approval? | No. It is feedback only. A final full-note verification of the latest complete revision is mandatory. | FR-21, FR-22. |
| Does unsupported evidence mean contradiction? | No. `UNSUPPORTED` is visibly distinct from `CONTRADICTED`; absent/invalid evidence is not highlighted as conflict. | Constitution I; Spec 004 finding invariants; FR-17. |
| What happens when a verification component fails? | Persist/retain the failed upstream run, create a critical operational review finding, and block approval. | Constitution II/VII; FR-22–FR-24. |
| Can the reviewer reject when verification fails? | Yes, with reviewer label and non-blank reason. | FR-24; rejection is a human disposition, not an approval assertion. |
| How is concurrent review editing handled? | `expectedRevision` compare-and-append; stale writers receive `409 STALE_REVISION`; no merge or overwrite. | Spec 001 versioning; FR-19. |
| Are upstream severity labels authoritative? | No. Spec 007 maps upstream facts/rules/statuses via deterministic `REVIEW_SEVERITY-v1`. | Constitution VII; FR-15. |
| How are ambiguous Spec 006 severity keys handled? | They default conservatively under the documented policy and must be resolved as a shared producer/consumer vocabulary before implementation. | Spec 006 free-form key; unresolved dependency retained. |
| Does this feature change sources, upstream findings, or medical records? | No. It appends review artifacts and successor note revisions only. | Constitution I–IV, VI; scope boundary. |
