import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { FounderDemoPage } from "../src/features/demo/FounderDemoPage";
import { verificationModeCopy } from "../src/features/documentation/DocumentationVerificationWorkspace";
import { WorkspaceProvider } from "../src/state/workspace";

const source = { source_id: "source-demo", source_version: 1, resident_test_id: "synthetic-founder-demo", language: "de-DE", transcript_text: "Die Bewohnerin verneint Übelkeit.", created_at: "2026-01-01T00:00:00Z" };
const note = { noteId: "note-demo", revision: 1, content: "Die Bewohnerin berichtet über Übelkeit.", status: "DRAFT", origin: "IMPORTED", sourceId: "source-demo", sourceVersion: 1, validationRunId: "validation-demo", facts: [], schemaVersion: "v1", rulesetVersion: "v1", sourceTextHash: "hash", normalizationPolicy: "v1", createdAt: "2026-01-01T00:00:00Z", createdBy: "synthetic-founder-demo", externalOrigin: { system: "demo", externalNoteId: "demo-1" } };

describe("founder guided demo", () => {
  it("labels offline replay and live LLM verification unambiguously", () => {
    expect(verificationModeCopy("OFFLINE_DEMO")).toMatchObject({
      label: "Offline replay",
      detail: expect.stringContaining("no live LLM request"),
    });
    expect(verificationModeCopy("LIVE_AI")).toMatchObject({
      label: "Live LLM verification",
      detail: expect.stringContaining("configured live LLM"),
    });
  });

  it("starts a persisted synthetic scenario from the one primary action", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (!String(input).includes("/demo-scenarios/founder-walkthrough/start")) return new Response("not found", { status: 404 });
      return new Response(JSON.stringify({ scenarioId: "founder-walkthrough-v1", scenarioVersion: "v1", syntheticOnly: true, source, note, correctedNote: source.transcript_text, steps: [
      { id: "INSPECT", title: "Inspect", instruction: "Inspect." }, { id: "VERIFY", title: "Verify", instruction: "Verify." }, { id: "CORRECT", title: "Correct", instruction: "Correct." }, { id: "REVERIFY", title: "Re-verify", instruction: "Re-verify." }, { id: "APPROVE", title: "Approve", instruction: "Approve." },
      ] }), { status: 201 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<MemoryRouter><QueryClientProvider client={queryClient}><WorkspaceProvider><FounderDemoPage /></WorkspaceProvider></QueryClientProvider></MemoryRouter>);
    const user = userEvent.setup();

    expect(screen.getByRole("heading", { name: /see how dexter guard/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start guided demo" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(String(fetchMock.mock.calls[0][0])).toContain("/demo-scenarios/founder-walkthrough/start");
  });
});
