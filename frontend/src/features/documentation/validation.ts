export const MIN_DOCUMENTATION_TEXT_LENGTH = 10;

export function isTranscriptValid(value: string): boolean {
  return value.trim().length >= MIN_DOCUMENTATION_TEXT_LENGTH;
}

export function isExternalNoteValid(value: string): boolean {
  return value.trim().length >= MIN_DOCUMENTATION_TEXT_LENGTH;
}
