import type { NoteResponse, NursingFact, SourceDocument } from "../../api/types";

export const MIN_DOCUMENTATION_TEXT_LENGTH = 10;
export const RESIDENT_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

export function isTranscriptValid(value: string): boolean {
  return value.trim().length >= MIN_DOCUMENTATION_TEXT_LENGTH;
}

export function isExternalNoteValid(value: string): boolean {
  return value.trim().length >= MIN_DOCUMENTATION_TEXT_LENGTH;
}

export function isResidentIdValid(value: string): boolean {
  return RESIDENT_ID_PATTERN.test(value);
}

export function transcriptValidationMessage(value: string): string | undefined {
  return isTranscriptValid(value) ? undefined : "Enter the original German caregiver transcript. It cannot be blank.";
}

export function residentIdValidationMessage(value: string): string | undefined {
  return isResidentIdValid(value) ? undefined : "Use a synthetic resident ID starting with a letter or number; only letters, numbers, dots, underscores, and hyphens are allowed.";
}

export function existingNoteValidationMessage(value: string): string | undefined {
  return isExternalNoteValid(value) ? undefined : "Paste the existing AI-generated nursing note before verification.";
}

function normalizedContent(value: string): string {
  return value.replace(/\s+/g, "");
}

function factSignature(fact: NursingFact): string {
  const semanticFact = { ...fact } as Partial<NursingFact>;
  delete semanticFact.factId;
  delete semanticFact.noteId;
  delete semanticFact.revision;
  return JSON.stringify(semanticFact, Object.keys(semanticFact).sort());
}

function factsAreIdentical(left: NursingFact[], right: NursingFact[]): boolean {
  return left.map(factSignature).sort().join("\u0000") === right.map(factSignature).sort().join("\u0000");
}

export function isDuplicateGeneratedNote(
  note: NoteResponse | undefined,
  source: SourceDocument | undefined,
  candidate: string,
  generatedFacts: NursingFact[] | undefined,
  generatedResidentId: string | undefined,
): boolean {
  if (!note || !source || note.origin !== "GENERATED" || !generatedFacts || !generatedResidentId) return false;
  return note.sourceId === source.source_id
    && note.sourceVersion === source.source_version
    && generatedResidentId === source.resident_test_id
    && normalizedContent(note.content) === normalizedContent(candidate)
    && factsAreIdentical(note.facts, generatedFacts);
}
