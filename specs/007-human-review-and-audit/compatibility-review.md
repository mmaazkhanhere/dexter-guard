# Spec 007 Compatibility Review

**Status:** Required pre-implementation evidence; not completed by this documentation-only change.

The available Spec 007 planning archive does not establish the concrete implementation
interfaces for Specs 001–006. This file records the required verification boundary without
claiming that unavailable source files, ports, repositories, or endpoint contracts were
inspected.

Before T005 or any dependent implementation begins, T001–T002 must record, for each upstream
specification:

- actual module/service owner and callable interface;
- contract and schema version identifiers;
- immutable source, note-revision, claim-set, run, and error-envelope identities;
- terminal status, timeout, bounded-retry, and idempotency behavior;
- repository transaction/migration constraints and test fixtures;
- exact adapter evidence used by the Spec 007 integration tests.

The required Spec 007 ports are reference-only adapters:

| Upstream | Required adapter output | Fail-closed condition |
| --- | --- | --- |
| Spec 001 | Immutable source/version and validated code-point spans | Missing source, version mismatch, or invalid offsets |
| Spec 002 | Immutable note revision and source binding | Mutable/in-place note or stale revision |
| Spec 003 | Current claim set for the exact note revision | Missing/empty/unbound claim set |
| Spec 004 | Terminal evidence run and findings | Unavailable, malformed, or mismatched run |
| Spec 005 | Terminal deterministic-validation run | Missing source facts/alignment or unavailable adapter |
| Spec 006 | Terminal coverage run and unresolved-item state | Malformed run or unresolved source item |

Until this report is completed, no implementation task may claim upstream integration
compatibility or approval readiness.
