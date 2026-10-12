# Spec 005 consumer handoff

The deterministic validation engine emits `ValidationRun` and `ValidationFinding` records under `DVE-CONTRACT-v1` and `DVE-RULESET-v1`.

Spec 007 should render `ruleId`, `ruleVersion`, `rulesetVersion`, `outcome`, source/claim/alignment IDs, evidence-reference IDs, expected/observed values, unit, reason code, and message. Both `FAIL` and `NOT_EVALUABLE` are non-success findings and have `requiresReview=true`; `NOT_EVALUABLE` means the comparison prerequisite was unavailable or ambiguous, not that the claim was correct.

Spec 005 intentionally exposes no severity, blocking, resolution, approval, clinical interpretation, or correction field. Spec 007 owns those policy decisions and must preserve deterministic findings alongside Spec 004 semantic findings.

Spec 008 can consume [the synthetic acceptance manifest](../../specs/005-deterministic-validation-engine/fixtures/spec005-acceptance-v1.json). The manifest records rule/ruleset versions and expected outcomes; benchmark thresholds remain outside online validation.
