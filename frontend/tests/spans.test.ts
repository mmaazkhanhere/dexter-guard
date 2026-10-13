import { describe, expect, it } from "vitest";
import { nonOverlappingSpans, projectSourceSpan, validSourceSpans } from "../src/features/verification/spans";

describe("source evidence span projection", () => {
  const source = { sourceId: "source-1", sourceVersion: 1 };
  it("uses Unicode code-point offsets, including astral characters", () => {
    const text = "A😀B";
    expect(projectSourceSpan(text, { ...source, start: 1, end: 2 })).toBe("😀");
  });
  it("rejects invalid identity and boundaries", () => {
    const text = "Ärger";
    expect(validSourceSpans(text, "source-1", 1, [{ ...source, start: 0, end: 99 }, { ...source, sourceVersion: 2, start: 0, end: 1 }])).toEqual([]);
  });
  it("keeps the first of overlapping backend spans", () => {
    expect(nonOverlappingSpans([{ ...source, start: 0, end: 4 }, { ...source, start: 2, end: 5 }])).toHaveLength(1);
  });
});
