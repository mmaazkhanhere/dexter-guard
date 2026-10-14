import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ToasterProvider } from "../src/components/shared/Toaster";
import { DocumentationVerificationPage } from "../src/features/documentation/DocumentationVerificationPage";
import { WorkspaceProvider } from "../src/state/workspace";

const source = { source_id: "source-1", source_version: 1, resident_test_id: "synthetic-1", language: "de-DE", transcript_text: "Die Bewohnerin berichtet guten Schlaf.", created_at: "2026-01-01T00:00:00Z" } as const;
const note = { noteId: "existing-note-1", revision: 1, content: "Bewohnerin berichtet starke Schmerzen.", status: "DRAFT", origin: "IMPORTED", sourceId: "source-1", sourceVersion: 1, validationRunId: "validation-1", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer", externalOrigin: { system: "synthetic-external-demo", externalNoteId: "external-1" } } as const;
const verification = { fullVerificationId: "full-existing-1", noteId: note.noteId, noteRevision: 1, source: { sourceId: "source-1", sourceVersion: 1 }, claimSetId: "claims-1", evidenceRunId: "evidence-1", deterministicValidationRunId: "validation-1", coverageRunId: "coverage-1", coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "verify-1", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" } as const;
const context = { contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: note.noteId, revision: 1, latestRevision: 1, noteStatus: "IN_REVIEW", source: { sourceId: "source-1", sourceVersion: 1 }, transcriptText: source.transcript_text, candidateNote: note.content, findings: [], decisions: [], suggestions: [], fullVerification: verification, approvalEligible: false } as const;

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><DocumentationVerificationPage /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);
}

describe("existing-note verification", () => {
  it("verifies the supplied note without generating a replacement and retains the review handoff", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/saved-examples")) return new Response("[]", { status: 200 });
      if (path.endsWith("/sources") && init?.method === "POST") return new Response(JSON.stringify(source), { status: 201 });
      if (path.endsWith("/notes/import") && init?.method === "POST") return new Response(JSON.stringify(note), { status: 201 });
      if (path.endsWith(`/reviews/${note.noteId}/full-verifications`) && init?.method === "POST") return new Response(JSON.stringify(verification), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}`)) return new Response(JSON.stringify(context), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("German transcript"), source.transcript_text);
    await user.click(screen.getByRole("button", { name: "Use existing note" }));
    await user.type(screen.getByLabelText("Existing AI-generated note"), note.content);
    await user.click(screen.getByRole("button", { name: "Verify existing note" }));

    await waitFor(() => expect(screen.getByText(/Candidate note.*existing-note-1.*IMPORTED/)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Continue to Human Review" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/notes/generate"))).toBe(false);
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/notes/import"))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith(`/reviews/${note.noteId}/full-verifications`))).toBe(true);
  });
});
