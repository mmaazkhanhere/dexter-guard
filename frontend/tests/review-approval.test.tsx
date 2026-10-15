import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
const cleanContext = { ...context, findings: [], approvalEligible: true } as unknown as ReviewContext;

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

  it("disables full verification while the editor differs from the saved revision", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith(`/reviews/${note.noteId}/audit`)) return new Response(JSON.stringify({ noteId: note.noteId, events: [] }), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}/revisions`) && init?.method === "POST") return new Response(JSON.stringify({ noteId: note.noteId, revision: 2 }), { status: 201 });
      if (path.includes(`/reviews/${note.noteId}/full-verifications`) && init?.method === "POST") return new Response(JSON.stringify({ ...verification, noteRevision: 2 }), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}`)) return new Response(JSON.stringify(cleanContext), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><SeedWorkspace /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);

    const editor = await screen.findByLabelText("Editable nursing note");
    const verifyButton = screen.getByRole("button", { name: "Run full verification" });
    expect(verifyButton).toBeEnabled();

    await user.type(editor, " Ergänzung");

    expect(verifyButton).toBeDisabled();
    expect(screen.getByText("Save the edited note as a new revision before running full verification.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input, request]) => String(input).includes("/full-verifications") && request?.method === "POST")).toBe(false);

    const auditReadsBeforeSave = fetchMock.mock.calls.filter(([input]) => String(input).endsWith(`/reviews/${note.noteId}/audit`)).length;
    await user.click(screen.getByRole("button", { name: "Save successor revision" }));
    await waitFor(() => expect(verifyButton).toBeEnabled());
    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    await waitFor(() => expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith(`/reviews/${note.noteId}/audit`)).length).toBeGreaterThan(auditReadsBeforeSave));

    const auditReadsBeforeVerification = fetchMock.mock.calls.filter(([input]) => String(input).endsWith(`/reviews/${note.noteId}/audit`)).length;
    await user.click(verifyButton);
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, request]) => String(input).includes("/full-verifications") && request?.method === "POST")).toBe(true));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith(`/reviews/${note.noteId}/audit`)).length).toBeGreaterThan(auditReadsBeforeVerification));
    const verificationRequest = fetchMock.mock.calls.find(([input, request]) => String(input).includes("/full-verifications") && request?.method === "POST");
    expect(JSON.parse(String(verificationRequest?.[1]?.body)).expectedRevision).toBe(2);
  });

  it("blocks approval immediately when a verified note has unsaved edits", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith(`/reviews/${note.noteId}/audit`)) return new Response(JSON.stringify({ noteId: note.noteId, events: [] }), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}`)) return new Response(JSON.stringify(cleanContext), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    }));
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><SeedWorkspace /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);

    await waitFor(() => expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled());
    await user.type(screen.getByRole("textbox", { name: "Editable nursing note" }), " Zusatz");

    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Unsaved changes are present");
  });

  it("ignores an older verification result that completes after a successor revision is saved", async () => {
    let resolveVerification!: (response: Response) => void;
    const pendingVerification = new Promise<Response>((resolve) => { resolveVerification = resolve; });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith(`/reviews/${note.noteId}/audit`)) return new Response(JSON.stringify({ noteId: note.noteId, events: [] }), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}/full-verifications`) && init?.method === "POST") return pendingVerification;
      if (path.includes(`/reviews/${note.noteId}/revisions`) && init?.method === "POST") return new Response(JSON.stringify({ noteId: note.noteId, revision: 2 }), { status: 201 });
      if (path.includes(`/reviews/${note.noteId}`)) return new Response(JSON.stringify(cleanContext), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><SeedWorkspace /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);

    const verifyButton = await screen.findByRole("button", { name: "Run full verification" });
    await user.click(verifyButton);
    await waitFor(() => expect(fetchMock.mock.calls.some(([input, request]) => String(input).includes("/full-verifications") && request?.method === "POST")).toBe(true));
    await user.type(screen.getByRole("textbox", { name: "Editable nursing note" }), " Zusatz");
    await user.click(screen.getByRole("button", { name: "Save successor revision" }));
    await waitFor(() => expect(screen.getByText(/Current persisted revision .* 2/)).toBeInTheDocument());

    resolveVerification(new Response(JSON.stringify({ ...verification, noteRevision: 1 }), { status: 200 }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText("Verification run recorded")).not.toBeInTheDocument();
  });
});
