# Spec 008 Clarifications

**Method:** Requirements clarification from the constitution, project architecture, and approved Specs 001–007 before technical planning. No missing document is represented as reviewed.

| Question | Resolution | Basis / impact |
| --- | --- | --- |
| What is the source of truth for evidence and scoring labels? | Immutable Spec 001 source versions are evidence authority; Spec 004 statuses, Spec 005 rules, and Spec 006 coverage outcomes retain their owners. Benchmark annotations supply scoring ground truth only. | Constitution I/IV; architecture; avoids duplicate verification. |
| Does missing evidence count as contradiction? | No. Missing evidence remains distinct from `CONTRADICTED`; it can support `UNSUPPORTED` only where annotations/policy say so. | Constitution I; Spec 004. |
| What counts as a successful detected error? | One finding must match the same annotated claim/missing fact and relevant discrepancy/status/value/evidence relation under `EVALUATION_MATCHING-v1`. Nearby warnings do not count. | User-provided evaluation rule; FR-29. |
| Can multiple warnings increase recall for one error? | No. Each error and finding is consumed once; extras are duplicates or unmatched warnings and affect burden/false-positive analysis. | Prevents double counting. |
| How do failures affect metrics? | They are retained as terminal case statuses. They are excluded only from metrics with no possible score, are counted in failure/unscorable counts, and critical errors default missed unless validly detected before failure. | Constitution VII; FR-29. |
| How is a zero denominator handled? | Return `NOT_APPLICABLE`, raw `0/0`, `value=null`, and a visible reason. | Avoids misleading 0%/100%. |
| Is a baseline allowed to use a different candidate note? | No. Candidate hash/ID must match in each pair. Mismatched pairs are invalid and cannot affect paired effects. | FR-28. |
| Does a detection result prove caregiver improvement? | No. Only observed paired human-review data may report review outcomes. Without it, show automated outcomes separately; simulated results are explicitly labelled. | Scope and FR-28. |
| Which threshold is approved? | Held-out critical-error recall ≥95%. No other threshold is created; all are `TBD`. | User requirement; Constitution V. |
| Are held-out results forbidden to view? | No. They are permitted for final evaluation/reporting, but prohibited as prompt/model/rule tuning or model-selection inputs. Every access/run is auditable. | FR-27; preserves a usable release gate. |
| What makes variants “closely related”? | Shared `scenarioFamilyId`, duplicate/near-duplicate source/candidate hash detection, and annotation review establish grouping. A family cannot cross splits. | FR-27; implementation must define the validator’s similarity method before enabling acceptance. |
| Is live inference mandatory for tests? | No. Deterministic mocked/saved fixtures are mandatory for CI. Live configured-model runs are optional, labelled non-deterministic, and separately tracked. | FR-31; reliable automation. |
| How are cost and tokens handled if unavailable? | Record `UNAVAILABLE` with reason and provider metadata; never convert missing data to zero cost/tokens. | FR-29/30. |
| What documents were unavailable? | No dedicated approved Spec 008 benchmark annotation guide, evaluation-run implementation contract, CI threshold policy, model-price catalog, or frontend dashboard architecture was found in inspected project materials. | These are explicit implementation discovery/design deliverables; no behavior is claimed as existing. |

