import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useApprove, useAudit, useFindingDecision, useFullVerification, useReject, useSaveRevision } from "../src/api/hooks";

function MutationHarness() {
  const audit = useAudit("note-1");
  const save = useSaveRevision();
  const verify = useFullVerification();
  const decide = useFindingDecision();
  const approve = useApprove();
  const reject = useReject();
  return <div>
    <div role="log">{audit.data?.events.map((event) => <span key={event.eventId}>{event.eventType}</span>)}</div>
    <button onClick={() => save.mutate({ noteId: "note-1", expectedRevision: 1, content: "Neue Notiz", reviewerLabel: "reviewer" })}>save</button>
    <button onClick={() => verify.mutate({ noteId: "note-1", expectedRevision: 1, reviewerLabel: "reviewer" })}>verify</button>
    <button onClick={() => decide.mutate({ noteId: "note-1", findingId: "finding-1", expectedRevision: 1, kind: "ACKNOWLEDGED", reviewerLabel: "reviewer" })}>decision</button>
    <button onClick={() => approve.mutate({ noteId: "note-1", expectedRevision: 1, fullVerificationId: "verification-1", reviewerLabel: "reviewer" })}>approve</button>
    <button onClick={() => reject.mutate({ noteId: "note-1", expectedRevision: 1, reviewerLabel: "reviewer", reason: "Not reliable" })}>reject</button>
  </div>;
}

describe("review mutation audit invalidation", () => {
  it.each(["save", "verify", "decision", "approve", "reject"])("invalidates the audit query after a successful %s", async (action) => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/audit")) return new Response(JSON.stringify({ noteId: "note-1", events: [] }), { status: 200 });
      if (path.includes("/revisions")) return new Response(JSON.stringify({ noteId: "note-1", revision: 2 }), { status: 201 });
      return new Response(JSON.stringify({ noteId: "note-1" }), { status: 200 });
    }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
    const user = userEvent.setup();
    render(<QueryClientProvider client={queryClient}><MutationHarness /></QueryClientProvider>);

    await user.click(screen.getByRole("button", { name: action }));

    await waitFor(() => expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ["audit", "note-1"] }));
  });

  it.each(["save", "verify", "decision", "approve", "reject"])("renders the newest audit event after %s succeeds", async (action) => {
    let auditReads = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/audit")) {
        auditReads += 1;
        const events = auditReads > 1 ? [{ eventId: "event-2", eventType: `${action.toUpperCase()}_RECORDED` }] : [];
        return new Response(JSON.stringify({ noteId: "note-1", events }), { status: 200 });
      }
      if (path.includes("/revisions")) return new Response(JSON.stringify({ noteId: "note-1", revision: 2 }), { status: 201 });
      return new Response(JSON.stringify({ noteId: "note-1" }), { status: 200 });
    }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const user = userEvent.setup();
    render(<QueryClientProvider client={queryClient}><MutationHarness /></QueryClientProvider>);

    await waitFor(() => expect(auditReads).toBe(1));
    await user.click(screen.getByRole("button", { name: action }));

    await waitFor(() => expect(screen.getByText(`${action.toUpperCase()}_RECORDED`)).toBeInTheDocument());
  });

  it("does not display a successful audit event when a mutation fails", async () => {
    let auditReads = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.includes("/audit")) {
        auditReads += 1;
        return new Response(JSON.stringify({ noteId: "note-1", events: [] }), { status: 200 });
      }
      return new Response(JSON.stringify({ code: "STALE_REVISION", message: "stale" }), { status: 409 });
    }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const user = userEvent.setup();
    render(<QueryClientProvider client={queryClient}><MutationHarness /></QueryClientProvider>);
    await waitFor(() => expect(auditReads).toBe(1));
    await user.click(screen.getByRole("button", { name: "approve" }));
    await waitFor(() => expect(screen.queryByText("APPROVE_RECORDED")).not.toBeInTheDocument());
    expect(auditReads).toBe(1);
  });
});
