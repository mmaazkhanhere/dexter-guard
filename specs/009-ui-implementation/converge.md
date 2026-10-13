# Spec 009 — Convergence and Release Readiness

**Feature:** `009-frontend-integration-and-vercel-deployment`  
**Project:** AI Nursing Documentation Reliability Engine  
**Status:** BLOCKED - local implementation verified; external release evidence remains unavailable
**Document type:** Post-implementation convergence checklist (project-specific artifact; not a required standard GitHub Spec Kit command output)  
**Scope:** React frontend, FastAPI integration, complete synthetic-only workflows, and Vercel deployment  
**Governing document:** `.specify/memory/constitution.md` (v1.0.0 in supplied project context)

> This is a *verification protocol*. Local evidence is recorded below; external deployment and persistence gates remain explicitly blocked. `PASS` is forbidden without reproducible evidence.

## 1. Convergence objective

Converge the implemented code, Spec 009 requirements (FR-34–FR-49), Specs 001–008 backend contracts, and the constitution into one demonstrably working, maintainable modular-monolith application. Completion requires real frontend-to-backend behavior, fail-closed review controls, durable synthetic-data persistence, meaningful test coverage, and a verified Vercel deployment or an explicitly reported external deployment blocker.

**Convergence outcomes**

- **PASS:** All mandatory gates have evidence and pass; a working deployment has been verified.
- **BLOCKED:** Required external access, credentials, an upstream backend contract, or platform capability prevents verification; no completion claim.
- **FAIL:** A requirement, safety invariant, test, or deployment check fails.
- **NOT ASSESSED:** No reliable evidence yet; default state for all checks.

**Release rule:** Any failed constitution MUST, any unresolved critical verification bypass, any real-data use, or any unverified approval decision is **NO-GO**, regardless of frontend polish. A blocked deployment means Spec 009 is not fully delivered, even when local code is ready.

## 2. Inputs and baseline capture

Before checking convergence, record:

| Item | Actual reference / location | Status |
|---|---|---|
| Constitution commit/version | `.specify/memory/constitution.md` | INSPECTED |
| Spec 009 `spec.md` revision | `specs/009-ui-implementation/spec.md` | INSPECTED |
| Spec 009 `plan.md` revision | `specs/009-ui-implementation/plan.md` | INSPECTED |
| Spec 009 `tasks.md` revision | `specs/009-ui-implementation/tasks.md` | UPDATED |
| Spec 009 OpenAPI / frontend mapping | `contracts/openapi.yaml`, `frontend/src/api/generated.ts` | VERIFIED LOCALLY |
| Backend Specs 001–008 revisions | `specs/001-*` through `specs/008-*` | REVIEWED FOR CONTRACTS |
| Application Git SHA | `51cb72a923615e95e88b6646db3e1434b5409a1c` | RECORDED |
| Test fixture / dataset version | Synthetic repository fixtures | VERIFIED SYNTHETIC-ONLY |
| Target Vercel project and runtime | `vercel.json`, Services + FastAPI | CONFIGURED; PREVIEW BLOCKED |
| Database environment and migration revision | No provider, credentials, or migration revision | BLOCKED |

Use the actual repository as authority for implemented routes, models, and deployment files; a proposed contract is not proof that an endpoint exists.

## 3. Architecture convergence gates

Current assessed results are summarized in Section 11; the original gate rows
below are retained as the protocol template.

| Gate | Pass criterion | Evidence | Status |
|---|---|---|---|
| ARC-01 Modular monolith | One repository with independent `frontend/` and `backend/` directories and one coherent application release | Repository tree, build logs | NOT ASSESSED |
| ARC-02 Backend ownership | FastAPI owns generation/verification, revisioning, review policy, persistence and evaluation metrics | Code review, backend tests | NOT ASSESSED |
| ARC-03 Typed HTTP boundary | React calls real versioned API endpoints using OpenAPI-aligned types; no competing TS clinical/business rules | Schema diff, integration tests | NOT ASSESSED |
| ARC-04 Deployment architecture | React web routes and `/api/v1/*` reach their intended targets under one public Vercel application URL | Production smoke tests | NOT ASSESSED |
| ARC-05 Durable state | Deployed revisions, decisions and audit events persist across reloads and function invocations; no reliance on ephemeral local SQLite | Persistence test | NOT ASSESSED |
| ARC-06 Minimal scope | No production auth, audio, multi-resident, clinical decisioning, microservices, or other excluded features added | Diff and architecture review | NOT ASSESSED |

## 4. Functional requirement convergence (FR-34–FR-49)

Current assessed results are summarized in Section 11; the original requirement
rows below are retained as the protocol template.

For each requirement, attach at least one passing test or reproducible observed behavior. Add code locations and test IDs to the actual tracking sheet.

| FR | Required integrated behavior | Suggested verification | Status |
|---|---|---|---|
| FR-34 | Usable desktop React shell with documented navigation | Browser smoke + accessible navigation | NOT ASSESSED |
| FR-35 | Submit German synthetic transcript and load saved source | Real API E2E: create and retrieve | NOT ASSESSED |
| FR-36 | Generate note or submit external candidate without generation | E2E for both branches; generation not called on external path | NOT ASSESSED |
| FR-37 | Structured observations, measurements, symptoms, actions visible | Contract and component tests | NOT ASSESSED |
| FR-38 | Addressable atomic claims, labels, statuses displayed | Integration test on real findings | NOT ASSESSED |
| FR-39 | Selecting finding highlights correct claim/source span and explanation | Span boundary + browser tests | NOT ASSESSED |
| FR-40 | Edits/suggestions explicit and revision-aware | E2E correction acceptance and cancel path | NOT ASSESSED |
| FR-41 | Independent claim-level decisions persisted | API/E2E adjudication test | NOT ASSESSED |
| FR-42 | Updated note can be reverified; stale findings invalidated | Revision race and reverify tests | NOT ASSESSED |
| FR-43 | Final approval requires backend-eligible latest full-note run | Negative and positive backend/API/E2E tests | NOT ASSESSED |
| FR-44 | Persisted revision and decision history survives page reload | DB-backed reload test | NOT ASSESSED |
| FR-45 | Evaluation dashboard shows authentic metrics and failures | Seeded evaluation API + UI tests | NOT ASSESSED |
| FR-46 | Both live inference and saved synthetic examples function | Live adapter smoke (when configured) + fixture E2E | NOT ASSESSED |
| FR-47 | Typed API client conforms to actual FastAPI OpenAPI | Generated-type/check contract CI | NOT ASSESSED |
| FR-48 | Entire application is reachable and functional on Vercel | Production URL, build ID, API and workflow smoke | NOT ASSESSED |
| FR-49 | Network, schema, provider, timeout, and DB failure states are truthful | Fault-injection / browser tests | NOT ASSESSED |

**Traceability rule:** Each FR must link to at least one acceptance scenario and one executable test or explicit inspection method. No “complete” status based solely on source files existing.

## 5. Mandatory evidence-integrity and safety gates

Current assessed results are summarized in Section 11; the original safety rows
below are retained as the protocol template.

| Gate | Adversarial scenario / assertion | Status |
|---|---|---|
| SAFE-01 | A highlight referencing the wrong `SourceDocument.version` is rejected, not presented as valid evidence | NOT ASSESSED |
| SAFE-02 | Candidate note text cannot serve as source evidence for that same candidate | NOT ASSESSED |
| SAFE-03 | A claim lacking source evidence is shown as UNSUPPORTED/UNCERTAIN as appropriate, not automatically CONTRADICTED | NOT ASSESSED |
| SAFE-04 | Accepting a suggestion cannot bypass source grounding or explicit user action | NOT ASSESSED |
| SAFE-05 | Editing revision N to N+1 invalidates old verification/approval eligibility, even if an old API response arrives later | NOT ASSESSED |
| SAFE-06 | Backend refuses approval unless the latest complete note revision and source version have a successful full-note verification | NOT ASSESSED |
| SAFE-07 | Unresolved critical discrepancies prevent approval at both UI and API layers | NOT ASSESSED |
| SAFE-08 | Prior note versions, findings, decisions, reviewer label and timestamps remain inspectable; no silent overwrite | NOT ASSESSED |
| SAFE-09 | Invalid model JSON, unavailable verifier, evidence error or timeout cannot convert into approval success | NOT ASSESSED |
| SAFE-10 | Client cannot claim save, decision, approval or verification success until backend confirms it | NOT ASSESSED |
| SAFE-11 | No real patient data in datasets, telemetry, screenshots or deployed examples | NOT ASSESSED |
| SAFE-12 | LLM credentials and database secrets are server-side, absent from browser bundles and git history | NOT ASSESSED |

**Required outcome:** Every SAFE gate must be PASS before declaring convergence. Failures are blockers, not risk-accepted cosmetic issues.

## 6. Testing and evidence matrix

The executed command results are recorded in Section 11.

Run the commands defined by the repository; the examples below are illustrative and MUST be adjusted to actual scripts. Record exact command, environment, Git SHA, result and artifact location.

| Suite | Expected coverage | Actual command | Result | Evidence |
|---|---|---|---|---|
| Frontend typecheck | Strict TS contracts | `cd frontend && npm run typecheck` (if defined) | NOT RUN | — |
| Frontend lint | Lint rules | `cd frontend && npm run lint` | NOT RUN | — |
| Frontend tests | Forms, highlights, review state, errors | `cd frontend && npm test -- --run` (if defined) | NOT RUN | — |
| Frontend build | Clean production compilation | `cd frontend && npm run build` | NOT RUN | — |
| Backend tests | Existing Specs 001–008 regressions | `cd backend && pytest` (if configured) | NOT RUN | — |
| API contracts | Backend OpenAPI matches generated frontend definitions | Project-specific schema diff | NOT RUN | — |
| E2E tests | Live backend, seeded synthetic fixtures, review flow | `npx playwright test` (if configured) | NOT RUN | — |
| Security checks | Secret scan, dependency vulnerabilities | Repository CI commands | NOT RUN | — |
| Production smoke | Frontend, API, database, lifecycle | Deployed URL tests | NOT RUN | — |

### Minimum end-to-end scenarios

- **E2E-01:** Submit a valid German transcript; generate draft; view source facts.
- **E2E-02:** Paste external note; verify without calling generator.
- **E2E-03:** Deliberately alter a numerical value; select contradiction and see correct source span.
- **E2E-04:** Add an unsupported clinical conclusion; show unsupported finding rather than fabricated contradiction.
- **E2E-05:** Edit flagged claim; previous verification becomes stale.
- **E2E-06:** Reverify updated full note; results match latest note revision.
- **E2E-07:** Attempt direct API approval with unresolved critical issue; reject.
- **E2E-08:** Resolve findings, reverify full note and approve eligible revision.
- **E2E-09:** Reload and confirm revision history, reasons, decisions persisted.
- **E2E-10:** Dashboard loads real evaluation metrics and a failure case; never fills absent values with invented zeros.
- **E2E-11:** Verification backend fails; no false success or approval.
- **E2E-12:** Delayed result for revision N arrives after N+1; UI discards stale result.
- **E2E-13:** Production deployed browser-to-API-to-database flow passes.

Use real endpoints for integrated tests. Mock external LLM behavior with controlled adapters for deterministic CI, then separately validate configured live inference. Do not claim complete live capability based only on mocks.

## 7. Evaluation and non-functional convergence

Evaluation data is displayed from backend routes; production benchmark and live
provider evidence remain external gates as recorded in Section 11.

Spec 009 *displays* backend evaluation metrics; Spec 008 defines their truth and thresholds. Confirm the UI neither recomputes a different denominator nor invents missing measurements.

| Check | Expected evidence | Status |
|---|---|---|
| EVAL-01 Dataset | ≥100 versioned synthetic German scenarios, protected holdout where mandated | NOT ASSESSED |
| EVAL-02 Paired comparison | Baseline and validated workflow use equivalent candidate notes | NOT ASSESSED |
| EVAL-03 Critical recall | Spec 008 held-out test reports ≥95% critical-error recall, with raw counts and limitations | NOT ASSESSED |
| EVAL-04 False positives | Supported-claim false-positive rate includes unnecessary UNCERTAIN review flags | NOT ASSESSED |
| EVAL-05 Completeness | Source-fact coverage and omissions correctly represented | NOT ASSESSED |
| EVAL-06 Performance | p50/p95 verification latency observed and displayed | NOT ASSESSED |
| EVAL-07 Cost | Additional verification cost measured separately from generation | NOT ASSESSED |
| EVAL-08 Operational burden | Warnings, manual decisions and corrections measured per note | NOT ASSESSED |
| EVAL-09 Provenance | Dataset/prompt/model/config IDs visible with evaluation runs | NOT ASSESSED |

Do not invent NFR targets that were never finalized; any missing thresholds remain `TBD` and must be resolved before claiming the corresponding release gate passed. Synthetic scores are not proof of clinical safety.

## 8. Vercel release convergence

The repository configuration is reviewed locally, but the production checks in
this section are blocked until Vercel and PostgreSQL access are available.

These checks must be performed using the **current supported Vercel project/runtime topology**, not an assumed routing convention.

1. **Build:** A clean repository checkout builds frontend and backend in the intended Vercel configuration.
2. **Routing:** `/` and client-side routes load React; `/api/v1/*` reaches FastAPI, not a static fallback.
3. **Database:** Production-environment PostgreSQL is reachable; schema migrations are applied; audit history persists across invocations.
4. **Configuration:** Required environment variables are documented; browser assets expose no secrets.
5. **Duration:** Live generation/verification fits configured function duration or fails closed with a truthful error; no silent timeout approval.
6. **Idempotency:** Retries do not duplicate note revisions, review decisions or approvals.
7. **Operations:** API errors, missing credentials and DB outages return predictable states.
8. **Smoke test:** Execute at least E2E-02, E2E-03, E2E-07, E2E-09, and E2E-13 against the deployed environment using synthetic data.
9. **Traceability:** Record deployment URL, commit SHA, deployment ID, UTC check time, and logs or CI links.
10. **Rollback:** Document the last known good deployment and how to restore it without destroying historical audit data.

**Vercel deployment record**

```text
Deployment URL:          BLOCKED - no authenticated Vercel project
Vercel deployment ID:    BLOCKED - no deployment attempted
Git SHA:                 51cb72a923615e95e88b6646db3e1434b5409a1c
Database/migration:      BLOCKED - no PostgreSQL provider or migration runtime
API smoke:               BLOCKED - no deployed URL
Browser E2E:             BLOCKED - Chromium binary unavailable after interrupted install
Live inference:          BLOCKED - no provider credentials
Checked at (UTC):        2026-10-13
```

If account access or secrets are unavailable, report `BLOCKED: external deployment verification` and clearly separate locally validated readiness from actually deployed functionality.

## 9. Drift, defects and reconciliation procedure

For every mismatch discovered between implementation and specs:

1. Record a defect with ID, severity, affected FR/SAFE gate, reproduction, expected and actual result.
2. Determine whether the cause is implementation drift, obsolete contract, missing backend capability, or ambiguous requirement.
3. Preserve constitution invariants; never “fix” failing approval tests by weakening safety behavior.
4. Amend the affected spec/contract first when requirements truly change; capture architecture-impacting choices in an ADR.
5. Implement the minimal correction; add a regression test reproducing the original problem.
6. Rerun impacted tests, then whole-workflow gates; record before/after evidence.
7. Update traceability and tasks; repeat until mandatory gates converge.

**Issue register template**

| ID | Requirement / gate | Severity | Observed discrepancy | Owner | Resolution / ADR | Retest evidence | Status |
|---|---|---|---|---|---|---|---|
| TBD | — | — | — | — | — | — | OPEN |

## 10. Completion checklist and decision

- [ ] Spec 009 FR-34–FR-49 each linked to passing acceptance evidence.
- [ ] No unresolved conflict with Specs 001–008, schemas, or frontend API mapping.
- [ ] All safety and evidence-integrity gates PASS.
- [ ] Backend remains the sole authority for verification and approval.
- [ ] All required test suites executed and passing.
- [ ] Evaluation dashboard shows authentic values and honest unavailable states.
- [ ] No excluded capabilities or real-data processing introduced.
- [ ] Persistent revision history verified after reload and fresh function execution.
- [ ] Production Vercel URL and deployment identity verified.
- [ ] Live and saved-demo workflows tested distinctly.
- [ ] Docs and quickstart commands checked against actual repository.
- [ ] Known issues, waivers (where constitution permits), and limitations documented.
- [ ] Maintainer/reviewer sign-off recorded.

**Convergence decision:** `BLOCKED`  
**Go / No-Go:** `NO-GO until mandatory evidence passes`  
**Reviewer:** `Codex automated convergence review`  
**Reviewed at (UTC):** `2026-10-13`  
**Release Git SHA:** `51cb72a923615e95e88b6646db3e1434b5409a1c`  
**Residual risks:** `PostgreSQL, Vercel access, Chromium browser, live provider, and production smoke remain blocked`

### Completion report to produce when checks have run

Summarize (a) FR-34–FR-49 coverage by code/test reference, (b) all SAFE gate results, (c) executed test commands and real outputs, (d) Spec 008 benchmark metrics and honest limitations, (e) actual Vercel deployment evidence, (f) remaining issues, and (g) a clear PASS/FAIL/BLOCKED release decision. Never mark PASS on the strength of a plan, screenshot, or mock-only demo.

## 11. Executed evidence and reconciliation

The checklist above is reconciled with the following actual local evidence. A
local PASS is not a production deployment PASS.

| Gate | Executed evidence | Result |
|---|---|---|
| Backend regression | `uv run pytest -q` | PASS - 341 tests passed; one existing Starlette/httpx deprecation warning |
| API contract/composition | `uv run pytest backend/tests/api/test_composition.py backend/tests/api/test_spec_009_contract.py -q` | PASS - 6 tests passed |
| Provider adapter | `uv run pytest -q backend/tests/nursing_notes/test_openai_compatible.py` | PASS - 6 tests passed |
| Frontend tests | `cd frontend; npm test -- --run` | PASS - 6 files, 11 tests |
| Frontend lint | `cd frontend; npm run lint` | PASS |
| TypeScript and production build | `cd frontend; npm run check` | PASS - Vite production build completed |
| OpenAPI client generation | `cd frontend; npm run api:generate` | PASS - generated client committed |
| Diff hygiene | `git diff --check` | PASS |
| Playwright browser E2E | `cd frontend; npm run test:e2e` | BLOCKED - Chromium was not installed; download was interrupted |
| Vercel build | `vercel build --yes` | BLOCKED - local Vercel token is invalid; no deployment attempted |

### Local implementation assessment

- FR-34 through FR-39, FR-42, FR-43, FR-45, FR-47, and FR-49 have local code and test evidence.
- FR-41 and FR-44 remain partial because review/audit persistence is not durable across fresh process instances.
- FR-46 remains partial because saved evaluation paths exist, but live provider execution has not been run against a configured endpoint.
- The generation path is now provider-agnostic through `OpenAICompatibleGenerationAdapter`; Groq and Gemini are selected by `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `backend/.env` or deployment secrets.
- FR-48 is blocked because Vercel preview and production routing were not verified.
- ARC-05 and SAFE-08 are blocked by the lack of PostgreSQL-backed repositories and migrations.
- SAFE-06 and SAFE-07 have local fail-closed guards, but deployed API and browser acceptance evidence is still required.

### Release blockers

1. Provision PostgreSQL, add migrations, and wire durable repositories for notes, reviews, audit events, and evaluation state.
2. Provide Vercel Services/project access, valid credentials, server-only secrets, and run `vercel build` plus preview smoke tests.
3. Install the Playwright Chromium test browser and execute the real browser workflow suite.
4. Run controlled live-inference smoke, timeout, and provider-error acceptance cases against the configured endpoint.

Until these blockers are removed, the correct convergence result is **BLOCKED / NO-GO**, not PASS. The repository is locally implemented and tested, but it is not yet a verified production deployment.
