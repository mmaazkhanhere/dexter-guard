import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { NoteResponse, ReviewContext, SourceDocument } from "../src/api/types";
import { VerificationResults } from "../src/features/verification/VerificationPage";

const source = { source_id: "source-results", source_version: 1, resident_test_id: "synthetic-results", language: "de-DE", transcript_text: "Frau Müller verneint Schmerzen. Die Temperatur beträgt 37,2 C.", created_at: "2026-01-01T00:00:00Z" } as unknown as SourceDocument;
const note = { noteId: "note-results", revision: 1, content: "Frau Müller klagt über Schmerzen. Die Temperatur beträgt 37,2 C.", status: "DRAFT", origin: "IMPORTED", sourceId: source.source_id, sourceVersion: 1, validationRunId: "validation-results", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer", externalOrigin: { system: "synthetic", externalNoteId: "external-results" } } as unknown as NoteResponse;
const verification = { fullVerificationId: "full-results", noteId: note.noteId, noteRevision: 1, source: { sourceId: source.source_id, sourceVersion: 1 }, claimSetId: "claims-results", evidenceRunId: "evidence-results", deterministicValidationRunId: "validation-results", coverageRunId: "coverage-results", coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "verify-results", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" } as const;
const finding = { reviewFindingId: "finding-contradiction", origin: "SPEC_005", noteId: note.noteId, noteRevision: 1, sourceId: source.source_id, sourceVersion: 1, claimId: "claim-pain", claimSpan: { startCodePoint: 0, endCodePointExclusive: note.content.indexOf("Die") }, upstreamStatus: "CONTRADICTED", ruleCode: "SEMANTIC_NEGATION", severity: "CRITICAL", severityPolicyVersion: "REVIEW_SEVERITY-v2", severityRationale: "Negation reversal changes the resident's reported symptom.", explanation: "The note says the resident reports pain, while the transcript says she denies pain.", evidence: { availability: "AVAILABLE", spans: [{ sourceId: source.source_id, sourceVersion: 1, start: 0, end: 32 }], excerpts: ["Frau Müller verneint Schmerzen."] }, state: "OPEN", createdAt: "2026-01-01T00:00:00Z" } as const;
const unsupported = { ...finding, reviewFindingId: "finding-unsupported", claimId: "claim-temperature", claimSpan: { startCodePoint: 37, endCodePointExclusive: 72 }, upstreamStatus: "UNSUPPORTED", severity: "MAJOR", severityRationale: "The changed measurement lacks source support.", explanation: "The changed measurement is not supported by the transcript.", evidence: { availability: "AVAILABLE", spans: [{ sourceId: source.source_id, sourceVersion: 1, start: source.transcript_text.indexOf("Die"), end: source.transcript_text.length }], excerpts: ["Die Temperatur beträgt 37,2 C."] } } as const;
const context = { contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: note.noteId, revision: 1, latestRevision: 1, noteStatus: "IN_REVIEW", source: { sourceId: source.source_id, sourceVersion: 1 }, transcriptText: source.transcript_text, candidateNote: note.content, findings: [unsupported, finding], decisions: [], suggestions: [], fullVerification: verification, approvalEligible: false } as unknown as ReviewContext;

describe("verification results presentation", () => {
  it("summarizes and prioritizes findings with classification, note, and source evidence", async () => {
    const user = userEvent.setup();
    render(<VerificationResults note={note} source={source} context={context} />);

    expect(screen.getByText("Total findings").parentElement).toHaveTextContent("2");
    expect(screen.getByText("Critical").parentElement).toHaveTextContent("1");
    expect(screen.getByText("Major").parentElement).toHaveTextContent("1");
    expect(screen.getByText("Unresolved").parentElement).toHaveTextContent("2");
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("Contradicted");
    expect(buttons[1]).toHaveTextContent("Unsupported");
    expect(screen.getByText(/Approval eligibility: Not eligible/)).toBeInTheDocument();
    expect(screen.getByText(/resolve the prioritized findings in Human Review/)).toBeInTheDocument();
    expect(screen.getAllByText(/Frau Müller verneint Schmerzen/).length).toBeGreaterThan(0);

    await user.click(buttons[0]);
    expect(screen.getByText("Problematic note text")).toBeInTheDocument();
    expect(screen.getAllByText(/The note says the resident reports pain/).length).toBeGreaterThan(0);
    expect(screen.getByText("Technical details")).toBeInTheDocument();
    expect(screen.getByText("Technical details").closest("details")).not.toHaveAttribute("open");
  });
});
