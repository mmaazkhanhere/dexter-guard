import { describe, expect, it } from "vitest";
import { isExternalNoteValid, isTranscriptValid } from "../src/features/documentation/validation";

describe("documentation input validation", () => {
  it("requires meaningful German transcript text", () => {
    expect(isTranscriptValid("   ")).toBe(false);
    expect(isTranscriptValid("Die Bewohnerin schläft gut.")).toBe(true);
  });

  it("requires meaningful external note text", () => {
    expect(isExternalNoteValid("kurz")).toBe(false);
    expect(isExternalNoteValid("Bewohnerin berichtet guten Schlaf.")).toBe(true);
  });
});
