import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ToasterProvider } from "../src/components/shared/Toaster";
import { DocumentationVerificationWorkspace } from "../src/features/documentation/DocumentationVerificationWorkspace";
import { WorkspaceProvider } from "../src/state/workspace";

const source = { source_id: "source-navigation", source_version: 1, resident_test_id: "synthetic-resident-7", language: "de-DE", transcript_text: "Frau Müller verneint Schmerzen.", created_at: "2026-01-01T00:00:00Z" } as const;
const note = { noteId: "note-navigation", revision: 1, content: "Frau Müller klagt über Schmerzen.", status: "DRAFT", origin: "GENERATED", sourceId: source.source_id, sourceVersion: 1, validationRunId: "validation-1", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer", generationRunId: "generation-1" } as const;
const verification = { fullVerificationId: "full-navigation", noteId: note.noteId, noteRevision: 1, source: { sourceId: source.source_id, sourceVersion: 1 }, claimSetId: "claims-1", evidenceRunId: "evidence-1", deterministicValidationRunId: "validation-1", coverageRunId: "coverage-1", coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "verify-1", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" } as const;
const context = { contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: note.noteId, revision: 1, latestRevision: 1, noteStatus: "IN_REVIEW", source: { sourceId: source.source_id, sourceVersion: 1 }, transcriptText: source.transcript_text, candidateNote: note.content, findings: [], decisions: [], suggestions: [], fullVerification: verification, approvalEligible: false } as const;

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter><QueryClientProvider client={client}><WorkspaceProvider><ToasterProvider><DocumentationVerificationWorkspace /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);
}

function RouteLinks() {
  const navigate = useNavigate();
  return <nav><button onClick={() => navigate("/documentation")}>Documentation</button><button onClick={() => navigate("/review")}>Human Review</button></nav>;
}

describe("documentation two-mode workspace", () => {
  it("blocks malformed resident IDs locally and identifies the field", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify([]), { status: 200 })));
    const user = userEvent.setup();
    renderWorkspace();

    await user.type(screen.getByLabelText("German transcript"), "Die Bewohnerin ist ruhig.");
    await user.clear(screen.getByLabelText("Synthetic resident identifier"));
    await user.type(screen.getByLabelText("Synthetic resident identifier"), "resident 01");

    expect(screen.getByLabelText("Synthetic resident identifier")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(/Use a synthetic resident ID/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate note & verify" })).toBeDisabled();
  });

  it("uses one segmented toggle and renders only the selected workflow", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ code: "NOT_FOUND", message: "not found" }), { status: 404 })));
    const user = userEvent.setup();
    renderWorkspace();

    expect(screen.getAllByRole("tab")).toHaveLength(2);
    expect(screen.getByRole("tab", { name: "Generate & Verify" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("button", { name: "Generate note & verify" })).toBeInTheDocument();
    expect(screen.getByLabelText("Example scenario")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load example scenario" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Existing AI-generated note")).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Verify Existing Note" }));

    expect(screen.getByRole("tab", { name: "Verify Existing Note" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Existing AI-generated note")).toBeInTheDocument();
    expect(screen.queryByLabelText("Example scenario")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Generate note & verify" })).not.toBeInTheDocument();
  });

  it("restores the transcript and resident identity after a Human Review route transition", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/saved-examples")) return new Response("[]", { status: 200 });
      if (path.endsWith("/sources") && init?.method === "POST") return new Response(JSON.stringify(source), { status: 201 });
      if (path.endsWith("/notes/generate") && init?.method === "POST") return new Response(JSON.stringify(note), { status: 201 });
      if (path.endsWith(`/reviews/${note.noteId}/full-verifications`)) return new Response(JSON.stringify(verification), { status: 200 });
      if (path.includes(`/reviews/${note.noteId}`)) return new Response(JSON.stringify(context), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={["/documentation"]}><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><WorkspaceProvider><ToasterProvider><RouteLinks /><Routes><Route path="/documentation" element={<DocumentationVerificationWorkspace />} /><Route path="/review" element={<div>Human review route</div>} /></Routes></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);

    await user.type(screen.getByLabelText("German transcript"), source.transcript_text);
    await user.clear(screen.getByLabelText("Synthetic resident identifier"));
    await user.type(screen.getByLabelText("Synthetic resident identifier"), source.resident_test_id);
    await user.click(screen.getByRole("button", { name: "Generate note & verify" }));
    await user.click(await screen.findByRole("button", { name: "Continue to Human Review" }));
    expect(screen.getByText("Human review route")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Documentation" }));

    expect(screen.getByLabelText("German transcript")).toHaveValue(source.transcript_text);
    expect(screen.getByLabelText("Synthetic resident identifier")).toHaveValue(source.resident_test_id);
    expect(screen.getByLabelText("German transcript")).toHaveAttribute("readonly");
    expect(screen.getByText(new RegExp(`Locked source .*${source.source_id} .*v${source.source_version}`))).toBeInTheDocument();
  });
});
