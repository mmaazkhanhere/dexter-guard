# Feature Specification: Nursing Note Generation

**Feature ID:** 002-nursing-note-generation  
**Status:** Draft for requirements review  
**Primary outcome:** A source-faithful, editable German nursing-note draft and structured nursing facts.

## Purpose

Caregiver observations are commonly recorded as informal German transcripts. This feature prepares those observations for clinical documentation by producing a clear, professional German nursing note and a structured representation of the stated nursing information. It is a documentation-generation and preparation component; it is not a reliability verifier, clinical decision-maker, or approval mechanism.

The feature must retain what the caregiver actually conveyed. In particular, it must not turn a negation into an assertion, uncertainty into certainty, a resident report into an observed fact, or an observation into a diagnosis.

## Scope

### In scope

- Generate an editable professional German nursing-note draft from an existing German source transcript.
- Extract structured facts for observations, symptoms, measurements, and actions from the same source.
- Preserve negation, uncertainty, attribution, numerical values, and units in both the prose and structured facts.
- Accept an externally supplied nursing-note draft without invoking generation.
- Persist source linkage, note origin, and revision lineage for generated and imported drafts.
- Surface controlled failures when generation output is unusable or malformed.

### Dependency boundary

FR-01 (source capture/availability) is owned by Spec 001. This feature receives an existing source reference and does not define how it was captured.

### Explicitly out of scope

- Diagnosing conditions, recommending treatment, or inventing clinical observations.
- Independently verifying claims, classifying claims, finding evidence, highlighting evidence, or approving a note.
- Caregiver approval workflows and benchmark/reporting dashboards.
- Automatically filling missing source information.

## Functional Requirements

### FR-02 — Generate professional German documentation

Given a valid German transcript referenced from Spec 001, the system shall create a readable, professionally worded German nursing-note draft. The draft shall be displayed or returned as editable content and shall have status `DRAFT`; it shall never be automatically verified or approved.

### FR-03 — Produce structured nursing facts

For a successfully generated draft, the system shall provide structured facts representing source-stated observations, symptoms, measurements, and actions. Every fact shall retain a source anchor, its fact type, and meaning-preservation fields needed to represent negation, uncertainty, attribution, numerical values, and units where present.

### FR-04 — Accept externally supplied notes

The system shall accept an externally supplied nursing-note draft, store it as a `DRAFT`, attach the supplied origin and provenance metadata, and make it available to the same downstream verification pipeline. Importing shall not invoke the generation model or fabricate structured facts not supplied with the import.

### FR-05 — Preserve meaning

The generated prose and extracted facts shall preserve the source meaning. Regression tests shall detect changes to negation, uncertainty, attribution, numerical values, and units. If the source does not establish a diagnosis, the generated note shall not state one as a fact.

## Conceptual Data Requirements

### Note draft

Each draft shall include:

- a stable draft identifier;
- editable German note content;
- lifecycle status fixed initially to `DRAFT`;
- origin: `GENERATED` or `IMPORTED`;
- the originating source reference when generated, or the declared external source/provenance when imported;
- creation time and creation actor/process identity;
- a revision number and a link to the preceding revision when revised;
- generation metadata only for generated drafts, including model/run identifier sufficient to trace the result without exposing hidden reasoning.

### Structured fact

Each fact shall include:

- a stable fact identifier and its parent draft/revision;
- type: `OBSERVATION`, `SYMPTOM`, `MEASUREMENT`, or `ACTION`;
- a normalized, human-readable statement that does not add meaning;
- source anchor or supplied external provenance;
- polarity (`AFFIRMED` or `NEGATED` when applicable);
- certainty (`CERTAIN`, `UNCERTAIN`, or source-equivalent qualifier when applicable);
- attribution (for example, resident-reported or caregiver-observed) when stated;
- numeric value and unit exactly as stated when applicable.

Absent information shall remain absent. The feature shall not infer an actor, time, diagnosis, value, unit, or certainty that the source does not provide.

## User Journeys

1. A caregiver transcript is available. A user requests a draft, receives professional German prose and structured facts, edits the draft as needed, and passes it to downstream review. It remains a draft.
2. A user already has a nursing-note draft. They import it with its source/origin details; it enters the same downstream verification path without a generation-model call.
3. A generation provider returns output that cannot be parsed or fails schema validation. The user receives a controlled error; no successful draft, structured facts, diagnosis, or substitute content is fabricated.

## Acceptance Scenarios

| ID | Given | Then |
| --- | --- | --- |
| GEN-001 | A valid German caregiver transcript | A readable professional German draft is generated and editable. |
| GEN-002 | A transcript with numerical measurements | The same numerical values and units appear in the draft and applicable structured facts. |
| GEN-003 | A transcript containing negation | Negation is retained in the draft and applicable facts. |
| GEN-004 | A transcript containing an uncertain observation | The uncertainty remains explicit; it is not converted to certainty. |
| GEN-005 | A resident-reported symptom | The result retains that the resident reported it rather than presenting it as independently observed. |
| GEN-006 | A transcript with symptoms, actions, and observations | Corresponding structured facts are programmatically available with source anchors. |
| GEN-007 | An externally supplied nursing note | It is stored as an imported draft and reaches downstream verification without a generation-model call. |
| GEN-008 | Malformed structured output from the generation provider | The operation fails in a controlled, observable way and does not create fabricated success data. |
| GEN-009 | A valid generated note | The note is editable and has `DRAFT` status; it is not verified or approved. |
| GEN-010 | Source language that could tempt an unsupported clinical inference | The note does not invent or assert a diagnosis. |

## Success Criteria

- FR-02 through FR-05 have passing acceptance and regression coverage.
- A German source transcript yields an editable professional German draft plus programmatically available facts.
- Imported notes enter the same downstream path without an LLM call.
- Negation, uncertainty, attribution, measurement values, and units are covered by regression tests.
- Malformed model output has a controlled failure path.
- Every generated or imported draft is traceable to source, origin, and revision metadata.
- No result produced by this feature is automatically verified or approved.
