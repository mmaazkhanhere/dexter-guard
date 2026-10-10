# Feature Specification: Nursing Note Generation

**Feature ID:** 002-nursing-note-generation  
**Status:** Draft for requirements review  
**Primary outcome:** A source-faithful, editable German nursing-note draft and structured nursing facts.

## Purpose

This feature converts an existing German caregiver transcript into a professional, editable nursing-note draft and structured nursing facts. It may also register an externally authored candidate note against the same source transcript. It prepares documentation for later verification; it neither verifies evidence nor approves documentation.

## Scope and boundaries

### In scope

- Generate editable professional German nursing prose from an immutable `SourceDocument` version.
- Extract source-linked observations, symptoms, measurements, and actions.
- Preserve source-stated negation, uncertainty, attribution, numerical values, and units.
- Import an external candidate note against an existing `SourceDocument` version without calling the generation model.
- Preserve note origin, evidence-source reference, and revision lineage.
- Reject malformed provider output through controlled errors.

### Out of scope

- Diagnosis, treatment recommendation, clinical evidence verification, claim classification, approval, or dashboards.
- Fabricating missing observations, values, actors, dates, certainty, or source references.
- Comprehensive semantic equivalence or clinical-inference judgment; those belong to downstream Specs 004 and 006.
- Real patient or employee data, production integration, regulatory certification, and nursing-home software integration. The PoC uses synthetic German data only.

FR-01 (source capture and storage) remains owned by Spec 001. This feature requires a resolvable `SourceDocument` and exact `sourceVersion`; it does not create either.

## Functional requirements

### FR-02 — Generate professional German documentation

Given an existing German `SourceDocument` and `sourceVersion`, the system shall create a readable, professionally worded German note with initial status `DRAFT`. The returned content shall be editable. Creation shall not verify or approve the draft.

### FR-03 — Produce structured nursing facts

For each successfully generated draft, the system shall expose structured facts for source-stated observations, symptoms, measurements, and actions. Each fact shall retain a source anchor and applicable meaning fields: polarity, certainty, attribution, value, and unit.

### FR-04 — Accept externally supplied notes

The system shall import an external candidate note only when it includes a resolvable `sourceId` and exact `sourceVersion`. It shall retain the candidate's external origin separately from its evidence source, store the note as `DRAFT`, and route it to downstream verification without invoking the generation model. Imported facts are optional and retain external provenance; none are generated or inferred by import.

### FR-05 — Preserve meaning within generation-time guardrails

Generation shall use limited, deterministic guardrails to reject invalid structured output and detect defined regressions in fixed fixtures: changed numeric values/units, invalid source anchors, and loss or inversion of explicitly represented polarity, uncertainty, or attribution fields. These guardrails do not prove semantic equivalence, clinical truth, or absence of all unsupported inference. A draft that passes them is **not evidence-verified**.

## Required record semantics

Every note revision shall contain a non-null evidence-source reference (`sourceId`, `sourceVersion`), editable content, `DRAFT` initial status, `GENERATED` or `IMPORTED` origin, creation metadata, and predecessor revision linkage when revised.

`externalOrigin` identifies where an imported candidate came from (for example, external system and external note identifier). It never replaces the evidence-source reference used by downstream verification.

Each fact shall include its parent revision, type (`OBSERVATION`, `SYMPTOM`, `MEASUREMENT`, or `ACTION`), source anchor, readable statement, and any stated polarity, certainty, attribution, value, and unit. Absent source detail stays absent; conflicting source statements remain distinct facts.

Facts are atomic: compound source statements are split when their parts can have different evidence outcomes. Each fact includes a resident subject identifier or explicit `UNKNOWN` state, temporal qualifier when stated, provenance reference, and the declared source-offset normalization policy. Source anchors are checked against the immutable source bytes/text for the validation run.

The normative field definitions are in `data-model.md`; the normative HTTP interface is in `contracts/notes-api.yaml`.

## Acceptance scenarios

| ID | Input | Required result |
| --- | --- | --- |
| GEN-001 | Valid German source transcript and version | A professional German `DRAFT` is returned and is editable. |
| GEN-002 | Source contains a numerical measurement | Fixture output preserves the exact value and unit in the corresponding fact; changed values or units are rejected. |
| GEN-003 | Source contains explicit negation | Fixture output records `NEGATED` polarity and does not assert the opposite. |
| GEN-004 | Source contains explicit uncertainty | Fixture output retains the uncertainty qualifier/field and does not mark it certain. |
| GEN-005 | Source contains a resident-reported symptom | Fixture output retains resident attribution and does not relabel it caregiver-observed. |
| GEN-006 | Source contains symptoms, actions, observations, and a measurement | Structured facts of each applicable type are returned with valid source anchors. |
| GEN-007 | External note plus valid `sourceId` and `sourceVersion` | Note is imported as `DRAFT`; evidence source and external origin remain distinct; generation adapter call count is zero. |
| GEN-008 | Provider returns malformed or schema-invalid output | Request returns a controlled error; no note or facts are persisted. |
| GEN-009 | Valid generated or imported note | Initial status is exactly `DRAFT`; no verified/approved state or transition is produced. |
| GEN-010 | Source could invite a diagnosis | Fixed fixture output that adds a diagnosis is rejected by the defined guardrail; passing output is still only a draft, not clinical or evidence verification. |

## Measurable acceptance measures

- **Schema validity:** 100% of valid fixed provider fixtures validate and persist exactly one draft revision; 100% of malformed/schema-invalid fixtures return `422` and persist zero revisions and zero facts.
- **Source-reference integrity:** 100% of persisted generated and imported revisions contain a `sourceId` and `sourceVersion` that resolve to the exact immutable `SourceDocument` version used for the request. An unknown or mismatched version returns `404`/`409` and persists nothing.
- **Import isolation:** Across the GEN-007 import test matrix, generation-adapter invocation count is exactly zero and every successful import has `origin=IMPORTED`, `status=DRAFT`, and a non-empty `externalOrigin` distinct from its evidence-source fields.
- **Fixed semantic-regression coverage:** The suite contains at least one deterministic fixture each for negation, uncertainty, attribution, numeric value, unit, and unsupported diagnosis. For every fixture, the stated expected accept/reject outcome in the table above is asserted; the suite is not a claim of general semantic verification.
- **Bidirectional fixture coverage:** The fixed fixture set includes one material source-span omission case and one draft-to-source mismatch case; each has an exact expected rejection or flagged outcome. This is a bounded generation guardrail, not comprehensive semantic verification.
- **Draft-state safety:** 100% of successful creation responses have `status=DRAFT`; no response contains `VERIFIED` or `APPROVED`.

## Success criteria

FR-02 through FR-05 are complete when all acceptance scenarios and measures pass, structured facts are programmatically accessible, imported candidates enter downstream verification with their evidence source intact and no model call, and every note revision has traceable origin, source, and revision metadata. Completion does not include downstream reliability verification.
