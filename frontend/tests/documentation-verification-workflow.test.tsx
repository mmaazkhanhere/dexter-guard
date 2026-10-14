import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ToasterProvider } from "../src/components/shared/Toaster";
import { DocumentationVerificationPage } from "../src/features/documentation/DocumentationVerificationPage";
import { WorkspaceProvider } from "../src/state/workspace";

const source = { source_id: "source-1", source_version: 1, resident_test_id: "synthetic-1", language: "de-DE", transcript_text: "Die Bewohnerin berichtet guten Schlaf.", created_at: "2026-01-01T00:00:00Z" } as const;
const note = { noteId: "note-1", revision: 1, content: "Bewohnerin berichtet guten Schlaf.", status: "DRAFT", origin: "GENERATED", sourceId: "source-1", sourceVersion: 1, validationRunId: "validation-1", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-reviewer", generationRunId: "generation-1" } as const;
const verification = { fullVerificationId: "full-1", noteId: "note-1", noteRevision: 1, source: { sourceId: "source-1", sourceVersion: 1 }, claimSetId: "claims-1", evidenceRunId: "evidence-1", deterministicValidationRunId: "validation-1", coverageRunId: "coverage-1", coverageUnresolvedSourceItems: 0, componentStatuses: [], status: "VALID", idempotencyKey: "verify-1", requestDigest: "digest", correlationId: "correlation", failureCode: null, failureMessage: null, createdAt: "2026-01-01T00:00:00Z", completedAt: "2026-01-01T00:00:00Z" } as const;
const context = { contractVersion: "REVIEW-AUDIT-CONTRACT-v1", noteId: "note-1", revision: 1, latestRevision: 1, noteStatus: "ELIGIBLE_FOR_APPROVAL", source: { sourceId: "source-1", sourceVersion: 1 }, transcriptText: source.transcript_text, candidateNote: note.content, findings: [], decisions: [], suggestions: [], fullVerification: verification, approvalEligible: false } as const;

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider><DocumentationVerificationPage /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);
}

describe("documentation and verification workflow", () => {
  it("automatically saves, generates, verifies, and reuses an unchanged candidate", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/saved-examples")) return new Response("[]", { status: 200 });
      if (path.endsWith("/sources") && init?.method === "POST") return new Response(JSON.stringify(source), { status: 201 });
      if (path.endsWith("/notes/generate") && init?.method === "POST") return new Response(JSON.stringify(note), { status: 201 });
      if (path.endsWith("/reviews/note-1/full-verifications") && init?.method === "POST") return new Response(JSON.stringify(verification), { status: 200 });
      if (path.includes("/reviews/note-1")) return new Response(JSON.stringify(context), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();
    expect(screen.getByRole("region", { name: "Documentation and verification workflow" })).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Synthetic resident identifier"));
    await user.type(screen.getByLabelText("Synthetic resident identifier"), source.resident_test_id);
    await user.type(screen.getByLabelText("German transcript"), source.transcript_text);
    await user.click(screen.getByRole("button", { name: "Generate & Verify" }));

    await waitFor(() => expect(screen.getByText("Verification completed. Review the findings before approval; the note is not yet eligible for approval.")).toBeInTheDocument());
    expect(screen.getByLabelText("German transcript")).toHaveAttribute("readonly");
    expect(screen.getByText("Read-only candidate note")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue to Human Review" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([input, request]) => String(input).endsWith("/sources") && request?.method === "POST")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([input, request]) => String(input).endsWith("/notes/generate") && request?.method === "POST")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([input, request]) => String(input).includes("/full-verifications") && request?.method === "POST")).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Generate & Verify" }));
    await waitFor(() => expect(screen.getByText("Existing note reused")).toBeInTheDocument());
    expect(fetchMock.mock.calls.filter(([input, request]) => String(input).endsWith("/notes/generate") && request?.method === "POST")).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([input, request]) => String(input).includes("/full-verifications") && request?.method === "POST")).toHaveLength(1);
  });

  it("keeps manual entry as the default and previews an example before loading it", async () => {
    const example = { exampleId: "example-1", title: "Guter Schlaf und ausreichendes Trinken", sourceId: "source-1", sourceVersion: 1, kind: "DOCUMENTATION", syntheticOnly: true };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/saved-examples")) return new Response(JSON.stringify([example]), { status: 200 });
      if (path.endsWith("/sources/source-1/versions/1")) return new Response(JSON.stringify(source), { status: 200 });
      return new Response(JSON.stringify({ code: "NOT_FOUND", message: "test route not found" }), { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByLabelText("German transcript")).toHaveValue("");
    await waitFor(() => expect(screen.getByRole("option", { name: "Guter Schlaf und ausreichendes Trinken" })).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText("Example transcript"), "example-1");
    await waitFor(() => expect(screen.getByText(source.transcript_text)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Use selected example" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("German transcript"), " Manuelle Ergänzung.");
    expect(screen.queryByRole("button", { name: "Use selected example" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("German transcript")).toHaveValue(" Manuelle Ergänzung.");
  });
});
