import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ToasterProvider } from "../src/components/shared/Toaster";
import { DocumentationVerificationWorkspace } from "../src/features/documentation/DocumentationVerificationWorkspace";
import { WorkspaceProvider } from "../src/state/workspace";

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<MemoryRouter><QueryClientProvider client={client}><WorkspaceProvider><ToasterProvider><DocumentationVerificationWorkspace /></ToasterProvider></WorkspaceProvider></QueryClientProvider></MemoryRouter>);
}

describe("documentation two-mode workspace", () => {
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
});
