# Convergence Review: Nursing Note Generation

**Status:** Pending implementation.

Convergence cannot determine code/spec completeness until the reviewer completes `checklist.md` and the implementation tasks are executed. When run after T017, evaluate:

- each FR-02–FR-05 against code and passing tests;
- GEN-001–GEN-010 against executable regression/integration coverage;
- generated/imported provenance and revision records in persisted data;
- proof that imports do not invoke the generation adapter;
- proof that successful notes remain `DRAFT` with no approval/verification transition.

If a gap is found, append a dependency-ordered task to `tasks.md`, implement it, and run convergence again. Report **Converged** only when no required gap remains.
