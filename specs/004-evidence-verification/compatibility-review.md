# Spec 004 — Compatibility Review: Specs 001–003

**Review outcome:** Compatible after the mappings recorded below. These mappings
are normative for Spec 004 integration and were checked against the named
upstream data models and contracts.

| Upstream contract | Spec 004 representation | Required integration check |
|---|---|---|
| Spec 001 `SourceDocument.source_id`, `source_version` | `sourceId`, `sourceVersion` | The camelCase HTTP mapping preserves the immutable `(source_id, source_version)` composite identity. |
| Spec 001 `SourceDocument.resident_test_id` | `ClaimInput.residentTestId` | Both use one known synthetic resident; the source, every resolved claim, and request value must match exactly. `UNKNOWN` is rejected by Spec 004. |
| Spec 001 `SourceSpan.start`, `end` | `SourceSpan.start`, `end` | Both use zero-based Unicode code-point/scalar-value, start-inclusive and end-exclusive offsets against exact unnormalized text. |
| Spec 002 `NoteRevision(noteId, revision)` | `noteId`, `noteRevision` | The request pair identifies the exact immutable candidate-note revision. |
| Spec 002 note provenance (`sourceId`, `sourceVersion`, `sourceTextHash`, `normalizationPolicy`) | source lookup and `inputDigest` | Spec 004 must retrieve the exact source version and may retain its digest; it does not normalize text or use note content as evidence. |
| Spec 003 `ExtractionSucceeded.extractionRunId` | `claimSetId` | `claimSetId` is exactly this immutable extraction-run ID, not a client-defined grouping. |
| Spec 003 `Claim.id`, `noteRevisionId`, `residentTestId` | `ClaimInput.claimId`, request note pair, `ClaimInput.residentTestId` | The claim resolver reads the extraction result by `claimSetId`, then proves membership, canonical note-revision association, and resident equality. It does not parse or manufacture an upstream `noteRevisionId`. |
| Spec 003 `EvidenceSourceReference` | source ID/version validation | The carried source reference must equal the requested source snapshot before semantic verification starts. |

## Resulting boundary

Spec 004 accepts only immutable identifiers and resolves source, note, and
claim material through the existing repositories/services. It neither mutates
upstream records nor accepts client claim text. This preserves Spec 001 source
immutability, Spec 002 revision identity, and Spec 003 extraction provenance.
