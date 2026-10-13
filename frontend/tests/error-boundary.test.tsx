import { render, screen } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "../src/components/shared/ErrorBoundary";

function BrokenView(): never {
  throw new Error("render failure");
}

describe("application error boundary", () => {
  beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => undefined));
  afterEach(() => vi.restoreAllMocks());

  it("shows a safe recovery state without exposing application content", () => {
    render(<ErrorBoundary><BrokenView /></ErrorBoundary>);
    expect(screen.getByRole("alert")).toHaveTextContent("Workspace unavailable");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
