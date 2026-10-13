# Review and audit contract notes

[`review-audit.openapi.yaml`](review-audit.openapi.yaml) is the versioned OpenAPI 3.1 contract for the Spec 007 backend endpoints. It follows the repository convention of a required `{ code, message }` error body and uses camelCase HTTP fields.

It deliberately references upstream artifacts by identifiers rather than accepting transcript text, claim content, evidence quotations, source facts, or alignments from clients as authoritative input. Exact source-span validation and excerpt derivation remain backend responsibilities. The current repository implements the backend route set; frontend coverage and complete acceptance evidence remain tracked in `tasks.md`.

Implementation status: the backend route set is now present in `src/human_review/api.py`; the
historical planning caveat below does not apply to backend route existence. Frontend and complete
acceptance evidence remain open in `tasks.md`.

The existing inspected routes for Specs 004–006 remain their owners' contracts. The route set in this directory is not asserted to exist until implementation tasks create it.
