import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppLayout } from "../src/components/layout/AppLayout";

describe("application shell", () => {
  it("exposes the three combined workflow workspaces", () => {
    render(<MemoryRouter><AppLayout /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Documentation & Verification" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Human Review" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Evaluation" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Evidence Verification" })).not.toBeInTheDocument();
    expect(screen.getByText("Synthetic data only")).toBeInTheDocument();
  });
});
