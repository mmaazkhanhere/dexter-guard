# Spec 007 Read-Only Consistency Analysis

**Analysis date:** 2026-10-12  
**Scope:** [spec.md](spec.md), [clarify.md](clarify.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/review-audit.openapi.yaml](contracts/review-audit.openapi.yaml), [quickstart.md](quickstart.md), [tasks.md](tasks.md), the constitution, architecture, ADRs 002–005, and Specs 001–006 contracts/docs inspected for this planning change.

## Method and result

No installed `specify`/`speckit` command or template directory was found under `.specify`; the repository's established `specify → clarify → plan → tasks → analyze` artifact convention was followed manually. This is a documentation consistency review, not a simulated tool execution or implementation/test claim.

**Result: internally consistent after reconciling Spec 006 policy keys, display-only suggestions, and unresolved source-item blocking.** No application source, dependency, test, or upstream contract was changed. The feature is ready for independent requirements-quality review; implementation is blocked only by the unchecked reviewer-owned checklist gate.

## Requirement coverage

| Requirement | Spec behaviour | Contract operation | Task coverage |
| --- | --- | --- | --- |
| FR-15 | `REVIEW_SEVERITY-v1` mappings | `ReviewFinding` | T009–T011 |
| FR-17 | Context, claims/evidence/highlights | `GET /reviews/{noteId}` | T009–T012 |
| FR-18 | Independent decisions | `POST .../decisions` | T013–T015 |
| FR-19 | Immutable revisions/conflict | `POST .../revisions` | T016–T017, T020 |
| FR-20 | Safe optional suggestions | Structured `SuggestedCorrection`; raw Spec 006 suggestions remain display-only | T018–T020 |
| FR-21 | Claim feedback only | `POST .../claim-reverification` | T021–T025 |
| FR-22 | Exact full-note aggregate | `POST .../full-verifications` | T021–T025 |
| FR-23 | Critical blocking | approval error contract | T026, T028 |
| FR-24 | Approval/rejection/adjudication | `POST .../approve`, `.../reject` | T013–T015, T026–T029 |
| FR-25 | Append-only audit | `GET .../audit` | T005–T008, T030–T032 |

## Evidence-integrity invariant coverage

| Invariant | Controls |
| --- | --- |
| Correct immutable source-version spans | Spec scope/HR-001/HR-012; ReviewFinding/EvidenceDisplay constraints; T010/T024. |
| Candidate never evidence for itself | Scope, plan highlighting boundary, database invariant 4; T010/T021. |
| Spec 006 policy keys / unresolved items | Explicit omission-key mapping; unresolved source items block approval; raw suggestions cannot be applied | Spec 006 CL-004, CL-010, CL-014, CL-015; T009, T018, T031 |
| Missing evidence differs from contradiction | Severity/context rules, HR-002, evidence availability schema; T010–T012. |
| Suggestions do not add unsupported facts | SuggestedCorrection `USABLE` support requirements, HR-011; T018–T019. |
| Edits invalidate obsolete verification | lifecycle, revision rules, HR-004/005/017; T016–T017/T024. |
| Final approval uses latest full verification | atomic policy, HR-007/015/016; T023/T026/T028. |
| History is never silently overwritten | append-only entities/invariants/audit, HR-010; T007–T008/T030. |
| Invalid/incomplete/failed verification cannot approve | full aggregate state and approval predicates, HR-014; T023–T028. |

## Boundary review

- Spec 001 retains source identity/span semantics and validation.
- Spec 002 retains note creation/revision ownership; Spec 007 requests an immutable successor rather than mutating it.
- Spec 003 retains claim extraction. Its review-facing invocation is not assumed available.
- Spec 004 retains evidence statuses and semantic verification; Spec 007 only maps severity/displays results.
- Spec 005 retains deterministic validation; its planned adapter retains sole ownership of resolving existing alignments.
- Spec 006 retains source coverage and upstream `severityPolicyKey`; final severity/approval remains Spec 007-owned.

## Resolved integration decisions

The formerly open choices are fixed in [clarify.md](clarify.md) and [research.md](research.md): explicit mappings for the actual Spec 006 omission keys, a Spec 005-owned reference-only deterministic-validation adapter, in-process claim extraction, idempotent SQLite schema initialization, a blocking policy for empty claim sets, display-only raw coverage suggestions, and blocking unresolved source items. No workaround that reparses source/note prose, guesses severity, or weakens approval eligibility is permitted.
