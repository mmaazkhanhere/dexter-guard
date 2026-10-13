import { expect, test } from "@playwright/test";

test("external candidate workflow uses the real source and import APIs", async ({ page }) => {
  await page.goto("/documentation");
  await page.getByLabel("Resident test ID").fill("synthetic-e2e-resident");
  await page.getByLabel("German transcript").fill("Die Bewohnerin berichtet guten Schlaf und trinkt ausreichend.");
  await page.getByRole("button", { name: "Submit transcript" }).click();
  await expect(page.getByText(/Source source-/)).toBeVisible();

  await page.getByRole("button", { name: "External note" }).click();
  await page.getByLabel("Candidate nursing note").fill("Bewohnerin berichtet guten Schlaf und trinkt ausreichend.");
  await page.getByRole("button", { name: "Import note" }).click();
  await expect(page.getByText(/Note note-/)).toBeVisible();
});
