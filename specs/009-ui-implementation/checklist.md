# Feature 009 Validation Checklist

This checklist is intentionally unmarked: creation of a plan is not evidence of implementation or verification.

- [ ] FR-34 through FR-49 appear in spec.md with at least one testable scenario each.
- [ ] All four workspaces and their user actions are represented in plan/tasks.
- [ ] Positive, negative, failure, boundary, and stale-revision cases have named tests.
- [ ] Existing API routes and separate-app composition gaps are accurately distinguished from proposed contracts.
- [ ] Source code-point offsets and immutable source/version identity survive to evidence rendering.
- [ ] Candidate notes are never treated as evidence for their own assertions.
- [ ] Missing evidence remains distinct from contradiction in labels and UI paths.
- [ ] Edit/suggestion behavior creates successors and cannot make stale results approval eligible.
- [ ] Backend blocks critical/incomplete/failed approval conditions; frontend only reflects/proactively disables.
- [ ] Evaluation metrics are backend-provided with denominator, state, and provenance.
- [ ] Browser contains no LLM/database credentials and synthetic-only boundary is visible.
- [ ] One-URL Vercel topology, plan limits, Services access, Postgres persistence, and smoke tests are evidenced.
- [ ] No excluded capability is introduced.
- [ ] Constitution compliance is reviewed in the implementation PR.

