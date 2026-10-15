import { expect, test } from "@playwright/test";

test("combined workflow saves, generates, and verifies before human review", async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    if (url.endsWith("/saved-examples")) return route.fulfill({ json: [] });
    if (url.endsWith("/sources")) return route.fulfill({ status: 201, json: { source_id: "source-e2e", source_version: 1, resident_test_id: "synthetic-e2e-resident", language: "de-DE", transcript_text: "Die Bewohnerin berichtet guten Schlaf und trinkt ausreichend.", created_at: "2026-01-01T00:00:00Z" } });
    if (url.endsWith("/notes/generate")) return route.fulfill({ status: 201, json: { noteId: "note-e2e", revision: 1, content: "Bewohnerin berichtet guten Schlaf und trinkt ausreichend.", status: "DRAFT", origin: "GENERATED", sourceId: "source-e2e", sourceVersion: 1, validationRunId: "validation-e2e", facts: [], generationRunId: "generation-e2e", schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer" } });
    if (url.includes("/full-verifications")) return route.fulfill({ json: { fullVerificationId: "full-e2e", noteId: "note-e2e", noteRevision: 1, source: { sourceId: "source-e2e", sourceVersion: 1 }, claimSetId: "claims-e2e", evidenceRunId: "evidence-e2e", deterministicValidationRunId: "validation-e2e", coverageRunId: "coverage-e2e", coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "key", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" } });
    if (url.includes("/reviews/note-e2e")) return route.fulfill({ json: { contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: "note-e2e", revision: 1, latestRevision: 1, noteStatus: "ELIGIBLE_FOR_APPROVAL", source: { sourceId: "source-e2e", sourceVersion: 1 }, transcriptText: "Die Bewohnerin berichtet guten Schlaf und trinkt ausreichend.", candidateNote: "Bewohnerin berichtet guten Schlaf und trinkt ausreichend.", findings: [], decisions: [], suggestions: [], fullVerification: null, approvalEligible: false } });
    return route.fulfill({ status: 404, json: { code: "NOT_FOUND", message: "test route not found" } });
  });
  await page.goto("/documentation");
  await page.getByLabel("Synthetic resident identifier").fill("synthetic-e2e-resident");
  await page.getByLabel("German transcript").fill("Die Bewohnerin berichtet guten Schlaf und trinkt ausreichend.");
  await page.getByRole("button", { name: "Generate note & verify" }).click();
  await expect(page.getByText("Review the note against its evidence")).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue to Human Review" })).toBeVisible();
});

test("documentation has no horizontal page overflow on mobile and tablet widths", async ({ page }) => {
  await page.route("**/api/v1/saved-examples", async (route) => route.fulfill({ json: [] }));

  for (const width of [390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/documentation");
    await expect(page.getByLabel("German transcript")).toBeVisible();

    const overflow = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      bodyWidth: document.body.scrollWidth,
    }));
    expect(overflow.documentWidth, `document overflow at ${width}px`).toBeLessThanOrEqual(overflow.viewportWidth);
    expect(overflow.bodyWidth, `body overflow at ${width}px`).toBeLessThanOrEqual(overflow.viewportWidth);
  }
});

test("first-time visitor completes the synthetic founder walkthrough", async ({ page }) => {
  const transcript = "Bei der morgendlichen Kontrolle beträgt die Temperatur der Bewohnerin 37,4 Grad Celsius. Die Bewohnerin verneint Übelkeit.";
  const flawed = "Bei der morgendlichen Kontrolle beträgt die Temperatur der Bewohnerin 38,4 Grad Celsius. Die Bewohnerin berichtet über Übelkeit. Eine deutliche Hautrötung wurde beobachtet.";
  const source = { source_id: "source-demo", source_version: 1, resident_test_id: "synthetic-founder-demo", language: "de-DE", transcript_text: transcript, created_at: "2026-01-01T00:00:00Z" };
  const note = { noteId: "note-demo", revision: 1, content: flawed, status: "DRAFT", origin: "IMPORTED", sourceId: "source-demo", sourceVersion: 1, validationRunId: "validation-demo", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-founder-demo", externalOrigin: { system: "demo", externalNoteId: "demo-1" } };
  let revision = 1;
  let verifiedRevision = 0;
  let approved = false;
  const verification = (noteRevision: number) => ({ fullVerificationId: `full-demo-${noteRevision}`, noteId: "note-demo", noteRevision, source: { sourceId: "source-demo", sourceVersion: 1 }, claimSetId: `claims-${noteRevision}`, evidenceRunId: `evidence-${noteRevision}`, deterministicValidationRunId: `validation-${noteRevision}`, coverageRunId: `coverage-${noteRevision}`, coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "demo", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" });
  const initialFindings = [
    ["finding-temperature", "CONTRADICTED", "The documented temperature differs from the source.", "CRITICAL"],
    ["finding-negation", "CONTRADICTED", "The source negates nausea, but the note records it as present.", "MAJOR"],
    ["finding-observation", "UNSUPPORTED", "The source does not establish the documented skin redness.", "MAJOR"],
  ].map(([reviewFindingId, upstreamStatus, explanation, severity]) => ({ reviewFindingId, origin: "SPEC_004", originRunId: "evidence-demo-1", originFindingId: `${reviewFindingId}-origin`, noteId: "note-demo", noteRevision: 1, sourceId: "source-demo", sourceVersion: 1, claimId: reviewFindingId, claimSpan: null, upstreamStatus, ruleCode: null, severity, severityPolicyVersion: "REVIEW_SEVERITY-v2", severityRationale: "Founder walkthrough evidence discrepancy.", explanation, evidence: { availability: "UNAVAILABLE", spans: [] }, state: "OPEN", createdAt: "2026-01-01T00:00:00Z" }));
  const context = (currentRevision: number) => ({ contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: "note-demo", revision: currentRevision, latestRevision: currentRevision, noteStatus: approved ? "APPROVED" : verifiedRevision === 2 ? "ELIGIBLE_FOR_APPROVAL" : verifiedRevision === 1 ? "IN_REVIEW" : "AWAITING_FULL_VERIFICATION", source: { sourceId: "source-demo", sourceVersion: 1 }, transcriptText: transcript, candidateNote: currentRevision === 2 ? transcript : flawed, findings: currentRevision === 1 ? initialFindings : [], decisions: [], suggestions: [], fullVerification: verifiedRevision === currentRevision ? verification(currentRevision) : null, approvalEligible: verifiedRevision === 2 && !approved });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = request.url();
    if (url.endsWith("/health")) return route.fulfill({ json: { status: "degraded", database: "unavailable", generationProvider: "UNAVAILABLE", verificationProvider: "OFFLINE_DEMO", generation: { mode: "unavailable", provider: null, model: null, configured: false, available: false, reason: "LLM provider configuration is missing." }, verification: { configured: false, available: false } } });
    if (url.endsWith("/saved-examples")) return route.fulfill({ json: [] });
    if (url.endsWith("/demo-scenarios/founder-walkthrough/start")) return route.fulfill({ status: 201, json: { scenarioId: "founder-walkthrough-v1", scenarioVersion: "v1", syntheticOnly: true, source, note, correctedNote: transcript, steps: [
      { id: "INSPECT", title: "Inspect the source", instruction: "Compare source and note." }, { id: "VERIFY", title: "Run verification", instruction: "Run verification." }, { id: "CORRECT", title: "Correct the note", instruction: "Correct it." }, { id: "REVERIFY", title: "Re-verify the new revision", instruction: "Verify again." }, { id: "APPROVE", title: "Approve as a human", instruction: "Approve it." },
    ] } });
    if (url.includes("/full-verifications")) {
      const body = request.postDataJSON() as { expectedRevision: number };
      verifiedRevision = body.expectedRevision;
      return route.fulfill({ json: verification(body.expectedRevision) });
    }
    if (url.endsWith("/revisions")) {
      revision = 2;
      return route.fulfill({ status: 201, json: { noteId: "note-demo", revision: 2, previousRevision: 1, noteStatus: "AWAITING_FULL_VERIFICATION", auditEventId: "event-save" } });
    }
    if (url.endsWith("/approve")) {
      approved = true;
      return route.fulfill({ status: 201, json: { dispositionId: "disposition-demo", noteId: "note-demo", noteRevision: 2, kind: "APPROVED", reviewerLabel: "synthetic-reviewer", reason: null, fullVerificationId: "full-demo-2", eligibilityPolicyVersion: "REVIEW_APPROVAL-v1", decidedAt: "2026-01-01T00:00:00Z" } });
    }
    if (url.includes("/reviews/note-demo/audit")) return route.fulfill({ json: { noteId: "note-demo", events: [] } });
    if (url.includes("/reviews/note-demo")) return route.fulfill({ json: context(revision) });
    return route.fulfill({ status: 404, json: { code: "NOT_FOUND", message: "test route not found" } });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Start guided demo" }).click();
  await expect(page.getByText("GUIDED DEMO · STEP VERIFY")).toBeVisible();
  await expect(page.getByRole("status", { name: "Verification mode" })).toContainText("Offline replay");
  await page.getByRole("button", { name: "Run guided verification" }).click();
  await expect(page.getByText("The documented temperature differs from the source.")).toBeVisible();
  await expect(page.getByText("The source negates nausea, but the note records it as present.")).toBeVisible();
  await expect(page.getByText("The source does not establish the documented skin redness.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Inspect and correct findings" })).toBeVisible();
  await page.getByRole("button", { name: "Inspect and correct findings" }).click();
  await page.getByRole("button", { name: "Apply evidence-supported demo correction" }).click();
  await page.getByRole("button", { name: "Save successor revision" }).click();
  await expect(page.getByRole("button", { name: "Run full verification" })).toBeEnabled();
  await page.getByRole("button", { name: "Run full verification" }).click();
  await expect(page.getByRole("button", { name: "Approve" })).toBeEnabled();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Synthetic note approved")).toBeVisible();
});
