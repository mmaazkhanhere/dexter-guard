import type { SourceSpan } from "../../api/types";

export function validSourceSpans(text: string, sourceId: string, sourceVersion: number, spans: SourceSpan[]): SourceSpan[] {
  const length = Array.from(text).length;
  return spans
    .filter((span) => span.sourceId === sourceId && span.sourceVersion === sourceVersion)
    .filter((span) => span.start >= 0 && span.end > span.start && span.end <= length)
    .sort((left, right) => left.start - right.start);
}

export function projectSourceSpan(text: string, span: SourceSpan): string | undefined {
  const codePoints = Array.from(text);
  if (span.start < 0 || span.end <= span.start || span.end > codePoints.length) return undefined;
  return codePoints.slice(span.start, span.end).join("");
}

export function nonOverlappingSpans(spans: SourceSpan[]): SourceSpan[] {
  const result: SourceSpan[] = [];
  for (const span of [...spans].sort((left, right) => left.start - right.start || left.end - right.end)) {
    if (!result.some((existing) => span.start < existing.end && span.end > existing.start)) result.push(span);
  }
  return result;
}
