# Spec 004 — Clarification Record

**Purpose:** Resolve specification ambiguities before design and task planning.  
**Status:** Resolved decisions are folded into [spec.md](spec.md).
**Method:** Decisions below are conservative where unsafe inference could make an ungrounded nursing note appear verified.

## Resolved decisions

| ID | Question | Decision |
|---|---|---|
| CL-001 | What is the unit verified? | One atomic claim from Spec 003. The verification service does not split, merge, rewrite, or otherwise repair claims. |
| CL-002 | What can count as evidence? | Only text in the immutable German source transcript identified by the request source ID and source version. The candidate note, other claims, retrieval scores, model memory, and prior runs cannot be evidence. |
| CL-003 | Which status values are permitted? | Exactly four primary statuses: SUPPORTED, UNSUPPORTED, CONTRADICTED, and UNCERTAIN. Operational failures are not a fifth evidence status. |
| CL-004 | How are source offsets defined? | Offsets are Unicode code-point positions in the exact immutable source string, zero-based, start-inclusive, and end-exclusive. Newlines, whitespace, and punctuation are characters; offsets are never calculated from normalized display text. |
| CL-005 | Is verifier quotation authoritative? | No. The service derives the returned quotation from the immutable source and validated offsets. A supplied quotation that differs from the derived string is an integrity failure. |
| CL-006 | What is the status precedence? | Explicit semantic conflict, then faithful support, then relevant unresolved ambiguity, then absence of support. This prevents absent evidence from becoming a contradiction and avoids treating model failures as evidence. |
| CL-007 | How does certainty affect status? | Apply annotation policy CERTAINTY-v1. A mere source qualification such as “vielleicht” or “unklar” versus a claim asserting the underlying fact is UNCERTAIN and carries a CERTAINTY discrepancy. It is CONTRADICTED only when the claim asserts confirmation or certainty and the source explicitly states that confirmation cannot be made or has been withheld. The finding records the policy version. |
| CL-008 | How does attribution affect status? | A patient report, third-party report, and confirmed clinical observation are different propositions. A report alone cannot support a claim that the symptom was clinically confirmed. The finding carries an ATTRIBUTION discrepancy; classification follows the available evidence and must not be SUPPORTED solely by the report. |
| CL-009 | How is a partial negation handled? | Negation scope is material. “Keine starken Schmerzen” does not establish “keine Schmerzen,” nor does it establish the opposite. The finding is normally UNCERTAIN if that is the only relevant evidence; it must include a NEGATION discrepancy. |
| CL-010 | When may unsupported have no span? | Only UNSUPPORTED may have no source span. SUPPORTED, CONTRADICTED, and UNCERTAIN must cite at least one relevant validated span, allowing a reviewer to check the basis. |
| CL-011 | Does the service own numeric/unit validation or omissions? | No. Numerical and unit mismatches are Spec 005; completeness and important omissions are Spec 006. Spec 004 may reject malformed claim contracts but must not silently take over those judgments. |
| CL-012 | What happens if one valid claim cannot be verified? | The run is non-successful. A successful run is all-or-nothing: every submitted valid claim has exactly one validated finding. No partial success is presented as authoritative. |
| CL-013 | What happens on malformed model output, timeout, or invalid evidence? | Persist or return a structured non-successful verification-run outcome when enough request identity exists; do not emit successful findings, approve the note, or substitute a fallback evidence status. |
| CL-014 | May retrieval decide the result? | No. Candidate-evidence retrieval narrows model attention only. For a short transcript, the verifier may compare each claim with the entire source. Retrieval absence cannot itself prove a claim unsupported. |

## Canonical handling examples

| Source transcript evidence | Candidate claim | Required outcome |
|---|---|---|
| “Patient verneint Schmerzen.” | “Patient hat keine Schmerzen.” | SUPPORTED. |
| No pain reference. | “Patient hat Schmerzen.” | UNSUPPORTED; absence is not contradiction. |
| “Patient verneint Schmerzen.” | “Patient hat Schmerzen.” | CONTRADICTED with NEGATION discrepancy. |
| “Vielleicht Schmerzen beim Umlagern.” | “Patient hat Schmerzen beim Umlagern.” | UNCERTAIN with CERTAINTY discrepancy under CERTAINTY-v1. |
| “Diagnose Exsikkose konnte nicht bestätigt werden.” | “Exsikkose ist bestätigt.” | CONTRADICTED with CERTAINTY and CLINICAL_INFERENCE discrepancies. |
| “Patient berichtet Schwindel.” | “Schwindel klinisch festgestellt.” | Not SUPPORTED solely on the report; ATTRIBUTION discrepancy. |
| “Keine starken Schmerzen.” | “Keine Schmerzen.” | UNCERTAIN with NEGATION discrepancy, unless other evidence resolves the broader claim. |

## Deferred implementation choices

These choices do not alter functional behavior and are intentionally delegated to planning and implementation:

- The repository-specific model provider, deployment mode, and credential mechanism.
- The exact persistence adapter and migration syntax already established by the project architecture.
- Whether the API completes a short run synchronously or returns a durable queued run, provided the published response contract and safe terminal states remain identical.
- The retrieval algorithm, provided it is advisory and cannot replace semantic comparison against the source.

## No remaining blocking product ambiguity

The status taxonomy, source authority, character-span convention, certainty policy, qualifier behavior, ownership boundaries, and safe-failure behavior are sufficiently decided to plan. Any later change to CERTAINTY-v1 requires a new policy version and regression cases; it must not silently change the meaning of prior runs.
