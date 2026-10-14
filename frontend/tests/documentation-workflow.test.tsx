import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { DocumentationPage } from "../src/features/documentation/DocumentationPage";
import { ToasterProvider } from "../src/components/shared/Toaster";
import { WorkspaceProvider } from "../src/state/workspace";

const source = { source_id: "source-1", source_version: 1, resident_test_id: "synthetic-1", language: "de-DE", transcript_text: "Die Bewohnerin berichtet guten Schlaf.", created_at: "2026-01-01T00:00:00Z" } as const;
const note = { noteId: "note-1", revision: 1, content: "Bewohnerin berichtet guten Schlaf.", status: "DRAFT", origin: "IMPORTED", sourceId: "source-1", sourceVersion: 1, validationRunId: "validation-1", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer", externalOrigin: { system: "synthetic", externalNoteId: "external-1" } } as const;

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><DocumentationPage /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);
}

describe("documentation workflow", () => {
  it("imports an external note without calling the generation endpoint", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/saved-examples")) return new Response("[]", { status: 200 });
      if (path.endsWith("/sources") && init?.method === "POST") return new Response(JSON.stringify(source), { status: 201 });
      if (path.endsWith("/notes/import") && init?.method === "POST") return new Response(JSON.stringify(note), { status: 201 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Resident test ID"), "synthetic-1");
    await user.type(screen.getByLabelText("German transcript"), source.transcript_text);
    await user.click(screen.getByRole("button", { name: "Submit transcript" }));
    await waitFor(() => expect(screen.getByText(/Source source-1 · v1 · de-DE/)).toBeInTheDocument());
    expect(screen.getByText(/Transcript saved/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "External note" }));
    await user.type(screen.getByLabelText("Candidate nursing note"), note.content);
    await user.click(screen.getByRole("button", { name: "Import note" }));
    await waitFor(() => expect(screen.getByText(/Note note-1 · revision 1 · IMPORTED/)).toBeInTheDocument());
    expect(screen.getByText(/Candidate note imported/)).toBeInTheDocument();

    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/notes/generate"))).toBe(false);
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/notes/import"))).toBe(true);
  });
});
