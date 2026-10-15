import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EvaluationWorkspace } from "../src/features/evaluation/EvaluationWorkspace";

const summary = {
  evaluationRunId: "eval-fixture",
  origin: "NEWLY_EXECUTED",
  runStatus: "SUCCEEDED",
  evaluationEvidence: "SAVED_FIXTURE",
  annotationReviewStatus: "INDEPENDENTLY_REVIEWED",
  dataset: { datasetId: "dataset-1", datasetVersion: "v1", datasetHash: "a".repeat(64), selectedSplit: "HELD_OUT" },
  metrics: [{ metricId: "critical-error-recall", metricKind: "RATE", state: "SCORED", value: 1, numerator: 1, denominator: 1 }],
};

describe("EvaluationWorkspace", () => {
  it("shows preloaded evidence and can launch a benchmark", async () => {
    const run = { ...summary, aggregateMetrics: summary.metrics, caseResults: [{ caseExecutionId: "case-1", scenarioId: "scenario-1", candidateId: "candidate-1", status: "FAILED", observedFindings: [], matchResults: [] }], comparison: null, configuration: { modelProvider: "OFFLINE", modelId: "offline-semantic-v1", modelVersion: "v1" } };
    const inspection = { evaluationRunId: "eval-fixture", caseExecutionId: "case-1", scenarioId: "scenario-1", status: "FAILED", benchmark: { datasetId: "dataset-1", datasetVersion: "v1" }, source: { transcriptText: "Patient reports dizziness." }, candidate: { noteBody: "Patient stable." }, expectedFindings: [{ errorId: "error-1", severity: "CRITICAL", description: "Dizziness omitted", sourceEvidenceSpans: [{ sourceId: "source-1", sourceVersion: 1, start: 0, end: 10 }] }], actualFindings: [], disagreements: [{ errorId: "error-1", disposition: "FALSE_NEGATIVE", dispositionLabel: "False negative", explanation: "The expected error has no valid observed finding." }], latency: { totalMs: 12 }, usageAndCost: { estimatedCost: 0 }, configuration: { modelProvider: "OFFLINE", modelId: "fixture", modelVersion: "v1" } };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/evaluation-runs") && init?.method === "POST") return new Response(JSON.stringify({ ...run, evaluationRunId: "eval-new" }), { status: 201 });
      if (path.endsWith("/evaluation-runs/eval-new")) return new Response(JSON.stringify({ ...run, evaluationRunId: "eval-new" }), { status: 200 });
      if (path.endsWith("/evaluation-runs/eval-fixture/cases/case-1")) return new Response(JSON.stringify(inspection), { status: 200 });
      if (path.endsWith("/evaluation-runs/eval-fixture")) return new Response(JSON.stringify(run), { status: 200 });
      return new Response(JSON.stringify([summary]), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><EvaluationWorkspace /></QueryClientProvider>);

    expect(await screen.findByText(/Evidence: SAVED_FIXTURE/)).toBeInTheDocument();
    expect(await screen.findByText(/Verifier: OFFLINE · model: offline-semantic-v1/)).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Inspect scenario scenario-1" }));
    expect(await screen.findByText("Patient reports dizziness.")).toBeInTheDocument();
    expect(await screen.findByText(/False negative/)).toBeInTheDocument();
    expect(await screen.findByText(/source-1 v1 \[0, 10\)/)).toBeInTheDocument();
    expect(await screen.findByText(/The expected error has no valid observed finding/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run synthetic benchmark" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/evaluation-runs"), expect.objectContaining({ method: "POST" })));
    await waitFor(() => expect(screen.getByText(/Critical-error recall/)).toBeInTheDocument());
  });
});
