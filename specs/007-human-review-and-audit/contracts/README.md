# Review and audit contract notes

[`review-audit.openapi.yaml`](review-audit.openapi.yaml) is the proposed OpenAPI 3.1 contract for new Spec 007 endpoints. It follows the repository convention of a required `{ code, message }` error body and uses camelCase HTTP fields.

It deliberately references upstream artifacts by identifiers rather than accepting transcript text, claim content, evidence quotations, source facts, or alignments from clients as authoritative input. Exact source-span validation and excerpt derivation remain backend responsibilities.

The existing inspected routes for Specs 004–006 remain their owners' contracts. The route set in this directory is not asserted to exist until implementation tasks create it.
