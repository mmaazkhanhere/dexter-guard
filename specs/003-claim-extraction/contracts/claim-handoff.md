# Spec 003 typed handoff contract

This is the service-boundary contract exposed to downstream consumers. It is
not an asynchronous event, message bus, outbox, evidence verdict, or approval
decision.

## Retrieval

```text
ClaimExtractionService.get_current_result(
    note_revision_id: str,
) -> ExtractionResult | None
```

The lookup is exact on `noteRevisionId` and the configured extractor version.
It returns only the newest persisted `SUCCEEDED` or `EMPTY` result for that
immutable revision. Failed results are never returned as verification-ready
results.

## Required consumer invariants

Every returned result carries:

- the exact `noteRevisionId` and immutable note body hash;
- the upstream `validationRunId` when the revision was resolved;
- the immutable `evidenceSourceReference`;
- extractor, provider, model, prompt, and output-schema versions;
- zero claims for `EMPTY`, or validated revision-bound claims for `SUCCEEDED`.

Spec 004 may use the claim spans and carried source reference for its own
verification workflow. Spec 003 does not compare transcript text, assign
support/contradiction, classify clinical validity, or approve a revision.
