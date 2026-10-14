# Feature Specification: Frontend Integration and Vercel Deployment

**Feature ID:** 009-ui-implementation  
**Status:** Draft — specification and implementation plan only  
**Scope:** Desktop React interface, typed integration with Specs 001–008, and one-URL Vercel deployment for synthetic demonstrations.

## Purpose

Provide a desktop-oriented interface for the existing nursing-documentation reliability workflow. The interface presents backend-produced records and decisions; it neither recreates extraction, evidence reasoning, deterministic validation, review policy, evaluation calculations, nor approval policy. The product remains a synthetic German-documentation PoC and must not claim medical truth or clinical safety.

## Scope and exclusions

In scope: browser presentation, form input, typed API consumption, immutable-revision awareness, evidence highlighting, human-review controls, history, evaluation reporting, and deployment of one modular-monolith application.

Excluded: audio/speech upload, multiple-resident disambiguation, real records, diagnosis, treatment advice, autonomous clinical decisions, nursing-home integration, regulatory certification, production authentication/authorization, mobile UI, microservices, message queues, training/fine-tuning, and medical-truth verification.

## Personas and preconditions

A reviewer operates only on synthetic German scenarios. The backend is reachable and authoritative for immutable versions, all business-critical state transitions, persisted decisions, and eligibility. A source has exactly one synthetic resident identity.

## Workspaces and user stories

### A. Documentation & Verification

**US-009-A1 (P1):** As a reviewer, I can enter or load a synthetic German transcript, inspect and correct it before the workflow persists it, so I can start from the intended source text.  
**US-009-A2 (P1):** As a reviewer, I can generate a professional note and automatically run the backend's complete verification workflow against the immutable transcript.  
**US-009-A3 (P1):** As a reviewer, I can view the read-only candidate note alongside backend-returned findings, statuses, severities, explanations, and source evidence before continuing to Human Review.

### C. Human Review

**US-009-C1 (P1):** As a reviewer, I can review a finding, explicitly accept or reject a usable correction, document a decision or adjudication, edit a candidate, and request re-verification.  
**US-009-C2 (P1):** As a reviewer, I can see stale status, server-provided approval eligibility, approve or reject only through backend commands, and reconstruct revisions and decisions.

### D. Evaluation

**US-009-D1 (P2):** As an evaluator, I can select a saved or live synthetic evaluation and inspect backend-computed reliability, latency, cost, burden, baseline-versus-validated comparison, and failures.  
**US-009-D2 (P2):** As an evaluator, I can inspect the case-level inputs behind displayed metrics without the frontend recalculating them.

## Functional requirements and acceptance scenarios

| ID | Requirement | Verifiable acceptance scenarios |
| --- | --- | --- |
| FR-34 | Provide a desktop web interface for the complete reliability workflow. | AC-34a: a 1280px-wide viewport exposes Documentation & Verification, Human Review, and Evaluation navigation. AC-34b: keyboard navigation and text labels make all actions available without color-only meaning. |
| FR-35 | Allow entry of a German synthetic transcript and selection of saved examples before generation. | AC-35a: valid de-DE transcript is persisted automatically when Generate & Verify begins and shows its returned source ID/version. AC-35b: blank/invalid input exposes backend field error without claiming it saved. AC-35c: selecting an example loads only its declared immutable source/version. AC-35d: a persisted transcript is shown as a locked snapshot; an explicit edit action is required before replacement text can create a new source. |
| FR-36 | Generate a professional German note and automatically perform complete verification. | AC-36a: Generate & Verify saves any unsaved transcript, creates a DRAFT note, and requests the backend's current full-note verification for that exact note/source revision. AC-36b: the generated note remains read-only in this workspace; corrections occur only in Human Review. AC-36c: provider failure/timeout has a failure state and no editable false-success record. AC-36d: repeating generation for an unchanged generated candidate is a no-op when whitespace-normalized content, semantic structured facts, resident identity, and source ID/version all match; no new provider request or candidate note is created. AC-36e: a failed, invalid, or unavailable verification remains visibly non-eligible and does not hide the generated candidate or imply approval. |
| FR-37 | Display backend-returned observations, symptoms, measurements, and actions. | AC-37a: facts are grouped by returned fact type with source anchors. AC-37b: absent fact fields display as absent, not inferred values. |
| FR-38 | Display individually addressable claims and their evidence statuses. | AC-38a: each claim row has its immutable ID, note span, status, explanation, and run reference. AC-38b: supported, unsupported, contradicted, and uncertain are textually distinct. |
| FR-39 | Highlight affected note claims and source spans with explanations and severities. | AC-39a: selecting a valid finding scrolls both immutable texts to its returned spans. AC-39b: invalid/missing evidence says unavailable and highlights nothing. AC-39c: rule and source-based findings carry visibly distinct provenance labels. |
| FR-40 | Allow manual editing and optional acceptance of source-grounded correction suggestions. | AC-40a: a manual save sends expected revision and shows returned successor only. AC-40b: an unusable/unsupported suggestion has no apply control. AC-40c: accepting a usable suggestion requires explicit confirmation and creates a successor, never in-place text mutation. |
| FR-41 | Allow individual finding decisions and documented adjudication where required. | AC-41a: acknowledgement, dispute, and adjudication submit the backend-required reviewer label/rationale. AC-41b: missing required rationale remains invalid. AC-41c: acknowledgement is not displayed as critical-issue resolution. |
| FR-42 | Support re-verification after edits and identify outdated results. | AC-42a: editing marks predecessor findings/runs stale immediately in the client and refreshes server context. AC-42b: a response for revision n cannot replace state for revision n+1. AC-42c: claim feedback is labelled not approval-eligible; full-note verification is distinct. |
| FR-43 | Show approval eligibility from backend latest complete-note verification. | AC-43a: only backend eligibility enables the approval command. AC-43b: unresolved critical, failed, incomplete, invalid, source-mismatched, or stale verification blocks approval. AC-43c: direct approval conflict presents the server error and does not show approved. |
| FR-44 | Display persisted revisions, findings, decisions, and outcomes. | AC-44a: audit timeline preserves prior revision content and event order. AC-44b: historical revision selection is read-only and clearly non-current. |
| FR-45 | Display backend reliability metrics, comparisons, latency, cost, burden, and failure analysis. | AC-45a: dashboard renders critical recall, supported-claim false-positive rate, classification accuracy, completeness, scenario detection, final quality, burden, p50/p95 latency, and cost from MetricResult. AC-45b: zero/not-applicable/unavailable states retain denominator/reason and are not rendered as zero success. |
| FR-46 | Support live backend inference and saved synthetic examples. | AC-46a: live action is labelled newly executed and retains its run ID. AC-46b: saved output is labelled historical; it is never presented as fresh inference. |
| FR-47 | Consume API contracts through a typed client with consistent request, response, loading, and error handling. | AC-47a: generated client types compile against the consolidated OpenAPI contract. AC-47b: loading, validation, conflict, timeout, malformed response, and unavailable-service states use one typed error presentation. |
| FR-48 | Deploy frontend and backend under one Vercel deployment URL. | AC-48a: production root serves the SPA and same-origin /api/v1 requests reach FastAPI. AC-48b: health check, source submission, and review-context smoke tests pass from the deployment URL. |
| FR-49 | Handle unavailable APIs, verification failures, invalid responses, persistence failures, and timeouts without false success. | AC-49a: non-success terminal runs remain visibly failed/non-eligible. AC-49b: retry is offered only for typed retryable operations and is idempotency-key safe. AC-49c: network timeout preserves the current revision and never marks it verified or approved. |
| FR-50 | Notify the reviewer of every persisted workflow action and terminal failure with the authoritative outcome, affected identity, and safety-relevant next state. | AC-50a: source/example and candidate-note actions announce success or failure, including source/note identity when created. AC-50b: save, verification, finding-decision, approval, and rejection actions announce their returned outcome and whether re-verification or eligibility review remains required. AC-50c: error notifications include the stable backend error code and do not claim a state change. |

## Required workflows

Documentation & Verification accepts or loads a transcript, lets the reviewer correct it before generation, and automatically persists the resulting source when Generate & Verify begins. It then creates a draft and requests the backend's complete verification for that exact note/source revision. The workspace displays the generated note read-only beside the backend's full-note results; it cannot correct or approve the note. Repeating the action for an unchanged generated candidate must reuse the existing candidate and current results when its whitespace-normalized content, semantic structured facts, resident identity, and source ID/version are unchanged.

Human Review creates immutable successors and decision events only through Spec 007. Any edit or accepted correction makes predecessor findings stale for approval. Claim-level re-verification supplies feedback only; final approval requires an eligible current full-note run. Rejection remains possible after a verification failure.

Evaluation uses Spec 008 evaluation-run records. It displays metrics and pairing exactly as provided, allows filtering/selection locally, and keeps historical saved results distinct from live runs.

## Mandatory invariants

1. Source spans always refer to the actual immutable source ID/version; UI text normalization must never calculate or alter offsets.
2. A generated or candidate note is never shown as independent evidence for itself.
3. Missing evidence remains distinct from explicit contradiction.
4. A suggestion is applicable only when the backend declares it usable/source-grounded; the UI never synthesizes correction facts.
5. A successor note revision invalidates predecessor findings for approval and preserves predecessor history.
6. Approval requires backend-confirmed, complete full-note verification for the latest note revision and applicable source version, with no unresolved critical discrepancy.
7. Invalid, timeout, malformed, or failed verification cannot enable approval.
8. The backend remains the final enforcer for revision state, decision persistence, and approval eligibility; client disabling is advisory.
9. LLM credentials exist only in server-side environment variables. No client build variable, API response, log, or source map may contain them.
10. Every asynchronous response is compared with its requested note/source/revision/run identity before it can update visible state.
11. Documentation & Verification never enables note editing, finding decisions, approval, or rejection; those actions remain exclusive to Human Review.

## Error and boundary behavior

The UI must distinguish input validation, not found, stale conflict, final-disposition conflict, provenance conflict, dependency unavailable, provider failure, malformed response, and timeout. It must retain readable prior data but mark it historical/stale when appropriate. It must not retry non-idempotent actions without a stable idempotency key. A request cancellation or route change may abort display work; it must not imply backend cancellation.

## Success criteria

All FR-34 through FR-49 scenarios are automated at the appropriate component, contract, or Playwright level; backend invariants stay intact; synthetic-only boundaries remain visible; and the deployed one-URL application satisfies the smoke checks in the deployment contract.

