# Spec 007 Validation Quickstart

This is a validation guide for the planned feature, not implementation code. The review API/UI and its synthetic fixtures do not yet exist at the time of this document.

## Prerequisites

- Python 3.11+ and the repository's existing virtual environment/tooling.
- The existing local FastAPI host and configured in-process services for Specs 001–006.
- Synthetic German source/note data only. Do not submit real resident or employee data.
- Before end-to-end review validation, implement the planned adapters in [research.md](research.md): in-process claim extraction, Spec 005 source-fact/alignment provision, and review persistence/router wiring.

## Existing commands

The following commands are already documented by repository configuration and are safe to use after implementation work adds tests. They do not implement Spec 007.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q src tests
git diff --check
```

Existing upstream APIs are documented in their own contracts:

- Spec 004: `POST /api/v1/verification-runs`
- Spec 005: `POST /api/v1/deterministic-validation-runs`
- Spec 006: `POST /api/v1/coverage-runs`

## Proposed commands and routes

These names are proposed for the implementation task and must not be treated as currently runnable:

```powershell
# Proposed only: launch the future review-enabled local application
.venv\Scripts\python.exe -m source_ingestion.main

# Proposed only: run the Spec 007 focused tests
.venv\Scripts\python.exe -m pytest tests\human_review -q
```

The proposed review endpoints are in [contracts/review-audit.openapi.yaml](contracts/review-audit.openapi.yaml).

## Synthetic walkthrough fixture

Use a fixture like the following, with a synthetic identifier:

```text
resident_test_id: SYN-007-01
source transcript: "Frau Beispiel berichtet am Morgen keinen Schmerz. Die Temperatur beträgt 36,8 °C. Beim Transfer benötigt sie Unterstützung durch eine Pflegekraft."
candidate note: "Frau Beispiel berichtet morgens Schmerzen. Temperatur 37,8 °C. Transfer selbstständig."
```

The fixture is designed to expose negation, numeric, and assistance discrepancies. It is not a medical scenario or medical truth claim.

## Planned review workflow validation

1. Create/resolve the synthetic immutable source via Spec 001, then generate or import the candidate as a Spec 002 draft.
2. Open the proposed `GET /api/v1/reviews/{noteId}` context for the latest revision.
3. Inspect each finding. Selecting the negation/numeric/transfer finding should show the relevant candidate claim and the source excerpt only if its source span is valid. A deliberately malformed or source-version-mismatched span must display `INVALID` evidence availability, not a highlight.
4. Try approving the initial note. The proposed approval endpoint must reject it because critical findings remain open and a valid final full-note verification is absent.
5. Correct the note manually or accept a separately validated `SuggestedCorrection`. A raw Spec 006 coverage suggestion remains display-only. Submit the current `expectedRevision`; verify the response creates the next immutable revision and leaves the original in audit history.
6. Trigger a claim-level re-verification for one changed claim. Verify its response declares `approvalEligible: false`.
7. Trigger full-note verification for the new revision. Confirm its aggregate references the exact source ID/version, current revision, new claim set, and terminal runs from Specs 004, 005, and 006.
8. Edit the note again after a successful aggregate. Confirm the prior aggregate is stale and approval is blocked until another full-note verification completes.
9. With a fully corrected synthetic note, no open critical discrepancy, complete required decisions, and a `VALID` aggregate for the latest revision, request approval. Confirm the disposition is recorded.
10. Separately force an upstream verification failure and reject the note. Confirm rejection succeeds with a non-empty reason.
11. Retrieve `GET /api/v1/reviews/{noteId}/audit`; confirm original/corrected revisions, decisions, suggestions, runs, and final disposition appear in sequence.

## Expected safety checks

| Check | Expected result |
| --- | --- |
| Unsupported finding with no evidence span | Shown as missing evidence, not contradiction. |
| Unsupported suggested wording | `UNUSABLE`; cannot be accepted. |
| Old verification after revision save | Historical/stale and ineligible for approval. |
| Malformed/failed full verification | Explicit failure; approval endpoint returns `409 APPROVAL_PRECONDITION_FAILED`. |
| Concurrent save/approval | Losing command gets `409 STALE_REVISION`/precondition failure and writes no invalid disposition. |
| Rejection after failed verification | Succeeds with reviewer label and reason. |
| Successful coverage run with unresolved source item | Approval remains blocked despite runtime completeness or acknowledgement/adjudication. |

## Test execution after implementation

Run the focused unit/contract/repository/API/UI/acceptance suites added by tasks T003–T031, then execute the existing repository suite and checks above. Fixtures must be synthetic German only and include HR-001 through HR-017. Record actual commands and results in the implementation PR/evaluation record; this planning document makes no claim that those tests have run.
