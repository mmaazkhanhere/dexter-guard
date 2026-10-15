import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { NoteResponse, ReviewContext, SourceDocument } from "../src/api/types";
import { ToasterProvider } from "../src/components/shared/Toaster";
import { ReviewWorkspace } from "../src/features/review/ReviewWorkspace";
import { useWorkspace, WorkspaceProvider } from "../src/state/workspace";

const source = { source_id: "source-approval", source_version: 1, resident_test_id: "synthetic-approval", language: "de-DE", transcript_text: "Die Bewohnerin verneint Schmerzen.", created_at: "2026-01-01T00:00:00Z" } as unknown as SourceDocument;
const note = { noteId: "note-approval", revision: 1, content: "Die Bewohnerin hat Schmerzen.", status: "DRAFT", origin: "IMPORTED", sourceId: source.source_id, sourceVersion: 1, validationRunId: "validation-approval", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer" } as unknown as NoteResponse;
const verification = { fullVerificationId: "full-approval", noteId: note.noteId, noteRevision: 1, source: { sourceId: source.source_id, sourceVersion: 1 }, claimSetId: "claims-approval", evidenceRunId: "evidence-approval", deterministicValidationRunId: "validation-approval", coverageRunId: "coverage-approval", coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "verify-approval", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" } as const;
const openFinding = { reviewFindingId: "finding-open", origin: "SPEC_004", noteId: note.noteId, noteRevision: 1, sourceId: source.source_id, sourceVersion: 1, claimId: "claim-pain", claimSpan: { startCodePoint: 0, endCodePointExclusive: note.content.length }, upstreamStatus: "CONTRADICTED", ruleCode: "SEMANTIC_NEGATION", severity: "CRITICAL", severityPolicyVersion: "REVIEW_SEVERITY-v2", severityRationale: "Negation reversal changes meaning.", explanation: "The note contradicts the source.", evidence: { availability: "AVAILABLE", spans: [{ sourceId: source.source_id, sourceVersion: 1, start: 0, end: source.transcript_text.length }], excerpts: [source.transcript_text] }, state: "OPEN", createdAt: "2026-01-01T00:00:00Z" } as const;
const context = { contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: note.noteId, revision: 1, latestRevision: 1, noteStatus: "IN_REVIEW", source: { sourceId: source.source_id, sourceVersion: 1 }, transcriptText: source.transcript_text, candidateNote: note.content, findings: [openFinding], decisions: [], suggestions: [], fullVerification: verification, approvalEligible: true } as unknown as ReviewContext;

function SeedWorkspace() {
  const { setNote, setSource } = useWorkspace();
  useEffect(() => {
    setSource(source);
    setNote(note);
  }, []);
  return <ReviewWorkspace />;
}

describe("human review approval guard", () => {
  it("blocks approval while an unresolved finding exists even if backend eligibility is true", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith(`/reviews/${note.noteId}/audit`)) return new Response(JSON.stringify({ noteId: note.noteId, events: [] }), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}`)) return new Response(JSON.stringify(context), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><SeedWorkspace /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);

    await waitFor(() => expect(screen.getByText("Review required. Unresolved issues must be resolved or adjudicated before approval.")).toBeInTheDocument());
    expect(screen.getByText("Approval blocked")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  });
});
