# Synthetic German Benchmark Annotation Guide

**Guide version:** `EVIDENCE_ANNOTATION-v1`  
**Matching policy:** `EVALUATION_MATCHING-v1`

Annotators use only synthetic German nursing scenarios. Each case has one source, one resident test ID, one scenario family, one protected split, and at least one fixed candidate note. Source and note spans are zero-based Unicode-code-point, start-inclusive/end-exclusive.

Annotate atomic candidate claims with the expected primary evidence status (`SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, or `UNCERTAIN`) and the exact discrepancy when an error exists. Annotate expected source facts separately for completeness; `CONTEXTUAL` facts and non-applicable facts never enter the completeness denominator.

Each error has exactly one affected target: a candidate claim or an expected source fact. Record category, approved severity, expected status, required discrepancy/rule, conflicting value/attribute where applicable, source spans, and provenance. A warning only counts as detection when it identifies the same target and required discrepancy. Missing evidence is not contradiction. An unnecessary `UNCERTAIN` finding on a correctly supported claim is a false positive.

Split assignment is family-first: create the family ID before assigning the case, then place the whole family in exactly one of `DEVELOPMENT`, `VALIDATION`, or `HELD_OUT`. Held-out labels, hashes, and reports are never inputs to prompt, rule, threshold, or model selection.

Independent review records disagreements and a resolution ID. No real patient, employee, or directly identifying information is permitted in source, notes, labels, telemetry, or reports.

