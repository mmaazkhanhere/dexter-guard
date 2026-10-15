import { describe, expect, it } from "vitest";
import type { NursingFact, NoteResponse, SourceDocument } from "../src/api/types";
import { isDuplicateGeneratedNote, isExternalNoteValid, isResidentIdValid, isTranscriptValid, residentIdValidationMessage } from "../src/features/documentation/validation";

describe("documentation input validation", () => {
  it("requires meaningful German transcript text", () => {
    expect(isTranscriptValid("   ")).toBe(false);
    expect(isTranscriptValid("Die Bewohnerin schläft gut.")).toBe(true);
  });

  it("requires meaningful external note text", () => {
    expect(isExternalNoteValid("   ")).toBe(false);
    expect(isExternalNoteValid("kurz")).toBe(true);
  });

  it("matches the backend synthetic resident ID shape and explains malformed values", () => {
    expect(isResidentIdValid("synthetic-resident_01")).toBe(true);
    expect(isResidentIdValid(" resident 01 ")).toBe(false);
    expect(isResidentIdValid("-resident")).toBe(false);
    expect(residentIdValidationMessage("resident 01")).toMatch(/only letters, numbers, dots, underscores, and hyphens/i);
  });

  it("detects an unchanged generated candidate without comparing generated IDs", () => {
    const source = { source_id: "source-1", source_version: 1, resident_test_id: "synthetic-1" } as unknown as SourceDocument;
    const facts = [{ factId: "note-a:r1:f1", noteId: "note-a", revision: 1, type: "OBSERVATION", statement: "Resident reports pain.", residentSubject: "synthetic-1", sourceAnchor: { sourceId: "source-1", sourceVersion: 1, start: 0, end: 20 }, provenance: "GENERATED_FROM_SOURCE" }] as unknown as NursingFact[];
    const note = { noteId: "note-a", revision: 1, content: "Resident has pain.", origin: "GENERATED", sourceId: "source-1", sourceVersion: 1, facts } as unknown as NoteResponse;

    expect(isDuplicateGeneratedNote(note, source, " Resident\n has pain. ", facts.map((fact) => ({ ...fact, factId: "note-b:r1:f1", noteId: "note-b" })), "synthetic-1")).toBe(true);
  });
});
