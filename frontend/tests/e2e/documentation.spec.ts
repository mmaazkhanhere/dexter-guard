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
  await page.getByRole("button", { name: "Generate & Verify" }).click();
  await expect(page.getByText(/Candidate note · note-e2e/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue to Human Review" })).toBeVisible();
});
