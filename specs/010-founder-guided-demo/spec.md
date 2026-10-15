# Spec 010: Founder Guided Demo

## Purpose

Give a first-time visitor one synthetic, evidence-backed walkthrough of Dexter Guard: inspect a flawed nursing note, verify it, correct a successor revision, re-verify it, and explicitly approve it.

## Requirements

- **FR-10-01:** `/` MUST present one primary action to start the guided demo and must label all demo content synthetic.
- **FR-10-02:** Starting the demo MUST create a normal immutable source and imported draft through existing source/note services; it MUST NOT create findings, decisions, or approval.
- **FR-10-03:** The scenario MUST include an altered measurement, a negation error, and a source-absent clinical observation that is classified as unsupported (not contradicted).
- **FR-10-04:** Guidance MUST advance from persisted source/note/revision/verification/approval state, not button clicks alone.
- **FR-10-05:** The walkthrough MUST use the existing verification and human-review workflows, preserving save-before-verify and human-only approval safeguards.
- **FR-10-06:** A completed walkthrough MUST show that approval was explicitly persisted and remains revision-bound.
- **FR-10-07:** The active documentation and verification workspace MUST state whether the walkthrough is using offline replay or configured live LLM verification, including that offline replay requires no LLM setup.

## Acceptance

A visitor can start the scenario from the landing page, run verification against the deliberately flawed imported note, inspect findings, save the supplied evidence-supported correction as a successor revision, verify that exact revision, and explicitly approve it without developer assistance.

## Scope and safety

All content is synthetic German nursing documentation. The demo is a product walkthrough, not an evaluation result, clinical assertion, diagnosis, or autonomous approval path.
