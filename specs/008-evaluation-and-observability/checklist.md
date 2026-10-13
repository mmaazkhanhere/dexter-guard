# Spec 008 Requirements-Quality Checklist

**Reviewer-owned artifact:** Check an item only after an independent reviewer determines that the documentation criterion is satisfied. Checked items do not claim implementation completion. This record documents the requirements-quality review; implementation and benchmark execution remain separate gates.

## Reviewer record

- **Reviewer:** Codex (automated requirements-quality review)
- **Date / artifact revision:** 2026-10-13 / Spec 008 documentation baseline after constitutional gap fixes
- **Decision:** REVIEW REQUIRED — amended contract and lifecycle artifacts
- **Exceptions and required remediation:** The prior requirements-quality approval covered the previous baseline. The amended API schemas, typed metrics, synthetic-demo tracking, synchronous lifecycle, and optional resident-context extension require re-review; implementation, accepted benchmark creation, compatibility discovery, and convergence evidence remain pending.

## Completeness

- [x] CQ-008-01 FR-26 through FR-33 each have observable behavior, acceptance scenario(s), task coverage, and an implementation verification method.
- [x] CQ-008-02 The benchmark requires at least 100 synthetic German scenarios and explicitly covers every required core error, ambiguity, paraphrase, and multiple-error category; resident-context mixing is optional extension coverage only.
- [x] CQ-008-03 Dataset, case, candidate, claim, error, source-fact, annotation-provenance, split, and configuration requirements are unambiguous.
- [x] CQ-008-04 All required metric definitions use the supplied operational definitions and report raw numerators/denominators.
- [x] CQ-008-05 Zero denominators, unscorable cases, invalid outputs, timeouts, interrupted runs, and partial failures have explicit visible treatment.
- [x] CQ-008-06 Baseline/validated comparison, starting-note quality, detection, human review, final-note quality, and review burden are distinct.
- [x] CQ-008-07 Saved historical results and newly executed live results are distinguishable and traceable.

## Clarity and consistency

- [x] CQ-008-08 Exact ground-truth matching prevents unrelated warnings, duplicate findings, one-to-many credit, and partial matches from inflating results.
- [x] CQ-008-09 SUPPORTED, UNSUPPORTED, CONTRADICTED, and UNCERTAIN retain existing Spec 004 meaning; missing evidence is never called contradiction.
- [x] CQ-008-10 Completeness uses manually annotated expected source facts rather than runtime system-extracted completeness.
- [x] CQ-008-11 The held-out split/family protection, duplicate detection, and no-silent-all-splits rule are testable.
- [x] CQ-008-12 The >=95% held-out critical-error recall target is the only new approved quantitative threshold; other thresholds are explicitly TBD.
- [x] CQ-008-13 Confidence intervals and variability treatment are stated without converting live model variability into a false deterministic claim.
- [x] CQ-008-14 The canonical `spec.md` is explicitly mapped to the constitution's `008-evaluation.md` reference, and the data model, OpenAPI contract, plan, and task terms/statuses agree.

## Evidence integrity, privacy, and scope

- [x] CQ-008-15 Source spans bind to correct immutable transcript versions and candidates are never independent evidence for themselves.
- [x] CQ-008-16 Evaluation cannot bypass stale-finding, latest-complete-verification, correction, audit, or failed-verification safeguards owned by Spec 007.
- [x] CQ-008-17 Configuration/run provenance is immutable, complete enough to reproduce a result, and content-minimised.
- [x] CQ-008-18 All benchmark, tests, telemetry, exports, examples, and reports are synthetic-only; no real healthcare information is introduced.
- [x] CQ-008-19 No prohibited scope—diagnosis, recommendation, EHR, auth, mobile, microservices, training, or clinical-truth verification—has been introduced.
- [x] CQ-008-20 Dependencies and missing supporting documents are named as discovery gates rather than silently assumed.

## Implementation readiness

- [x] CQ-008-21 Tasks are dependency ordered; deterministic work, live variability work, contracts, repositories, runner, reporting, and regression tests are separated.
- [x] CQ-008-22 The headless evaluation path does not depend on React.
- [x] CQ-008-23 Failure and unresolved-regression outcomes cannot appear as successful benchmark/release outcomes.
- [x] CQ-008-24 Aggregate reports can be traced to individual cases, findings, match dispositions, and underlying immutable references.

## Amendment review criteria

- [ ] CQ-008-25 The OpenAPI contract uses explicit reusable schemas for run configuration, case results, finding matches, comparisons, operational metrics, and failure/latency/cost entities, with no unrestricted generic run-result objects.
- [ ] CQ-008-26 Metric responses use tagged rate, count-per-note, and duration/cost distribution types with units, aggregation methods, policy versions, raw counts/observations, and confidence intervals where meaningful.
- [ ] CQ-008-27 Synthetic demonstration tracking accepts only immutable upstream references from Specs 001–007 and cannot create a duplicate ingestion or generation workflow.
- [ ] CQ-008-28 The local POST API is explicitly synchronous and terminal; run identity/configuration may be created before execution, while terminal results become immutable and intermediate lifecycle states are not returned by this endpoint.
- [ ] CQ-008-29 Resident-context mixing is optional extension coverage and cannot become a dependency of the core benchmark or release gate without an approved upstream context contract.

