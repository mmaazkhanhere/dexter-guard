# Spec 008 Upstream Adapter Matrix

This matrix is reference-only. The evaluation layer stores upstream identifiers and maps producer outputs into `ObservedFinding`; it never recomputes producer reliability logic.

| Producer | Input identity retained | Output fields mapped | Failure handling |
|---|---|---|---|
| Spec 004 | source, source version, note revision, claim set, verification run | claim ID, evidence status, discrepancies, evidence spans, producer run | failed verification is a failed case; no guessed finding |
| Spec 005 | note/source/claim revision and validation run | rule code/outcome as discrepancy or outcome | invalid/missing run is explicit failure |
| Spec 006 | source-fact extraction run, claim set, coverage run | source-fact ID, coverage outcome, source spans, related finding refs | unresolved provider/coverage remains visible and unscorable where required |
| Spec 007 | note revision, full verification, review decisions/audit | observed final revision, decisions, correction actions | unavailable is `UNAVAILABLE`; no simulated result is presented as observed |

The adapter contract requires a terminal upstream run and immutable references. It does not accept arbitrary source/note text as a substitute for upstream artifacts.

