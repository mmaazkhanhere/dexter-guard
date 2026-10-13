import { describe, expect, it } from "vitest";
import { shouldApplyNoteRevision } from "../src/state/workspace";
import type { NoteResponse } from "../src/api/types";

const note = (noteId: string, revision: number): NoteResponse => ({
  noteId, revision, content: `Revision ${revision}`, status: "DRAFT", origin: "IMPORTED",
  sourceId: "source-1", sourceVersion: 1, validationRunId: "validation-1", facts: [],
  schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1",
  createdAt: "2026-01-01T00:00:00Z", createdBy: "test",
});

describe("revision-aware workspace state", () => {
  it("rejects a response from an older revision", () => {
    expect(shouldApplyNoteRevision(note("note-1", 2), note("note-1", 1))).toBe(false);
  });

  it("rejects a response for a different note identity", () => {
    expect(shouldApplyNoteRevision(note("note-1", 1), note("note-2", 1))).toBe(false);
  });

  it("accepts a successor revision", () => {
    expect(shouldApplyNoteRevision(note("note-1", 1), note("note-1", 2))).toBe(true);
  });
});
