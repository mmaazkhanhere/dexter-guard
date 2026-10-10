# Convergence Review: Nursing Note Generation

**Status:** Pending implementation and requirements review.

After T020, verify code against `spec.md`, `data-model.md`, `contracts/notes-api.yaml`, and `plan.md`:

- all successful revision rows have a non-null source ID and exact source version;
- import preserves separate external-origin/evidence-source records and makes zero generation calls;
- the fixed GEN-001–GEN-010 fixtures have their specified result;
- malformed outputs and source mismatches persist nothing;
- no successful path returns a verified or approved status;
- validation success is never presented as evidence verification.

Append dependency-ordered tasks to `tasks.md` for every gap and rerun convergence until no required gap remains.
