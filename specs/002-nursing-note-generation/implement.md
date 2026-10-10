# Implementation Record: Nursing Note Generation

## Gate status

**Not started.** `checklist.md` is intentionally reviewer-owned and currently has unchecked requirements-quality items. Per the Spec Kit workflow, do not begin implementation or alter checklist markers until a reviewer completes that review.

## Execution order after the gate

1. Complete T001 and T002 to apply the project constitution and existing architectural conventions.
2. Complete foundation and generation tasks T003–T009.
3. Complete import/revision tasks T010–T012.
4. Complete test tasks T013–T017.
5. Re-run analysis (T018) and convergence (T019).

## Invariants to verify during implementation

- Every successful note starts as `DRAFT` and is editable.
- Generated content and facts retain source anchors and provenance.
- No model result is treated as successful before strict validation.
- Import has no generation-model call path.
- No generated or imported note is verified or approved here.
