import { useState } from "react";
import { useEvaluationRun, useEvaluationRuns } from "../../api/hooks";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import type { EvaluationMetric } from "../../api/types";

const metricIds = [
  ["critical-error-recall", "Critical-error recall"],
  ["supported-claim-false-positive-rate", "Supported-claim false-positive rate"],
  ["claim-classification-accuracy", "Claim classification accuracy"],
  ["completeness", "Completeness"],
  ["scenario-level-detection", "Scenario-level detection"],
  ["review-burden-warnings", "Review burden"],
  ["verification-latency", "Verification latency"],
  ["additional-inference-cost", "Additional inference cost"],
] as const;

function metricValue(metric: EvaluationMetric | undefined): string {
  if (!metric || metric.state !== "SCORED") return "UNAVAILABLE";
  if (metric.metricKind === "RATE") return metric.value == null ? "UNAVAILABLE" : `${(metric.value * 100).toFixed(1)}%`;
  if (metric.metricKind === "DURATION_DISTRIBUTION") return metric.p50 == null ? "UNAVAILABLE" : `p50 ${metric.p50.toFixed(0)} ms · p95 ${metric.p95?.toFixed(0) ?? "—"} ms`;
  if (metric.metricKind === "COST_DISTRIBUTION") return metric.p50 == null ? "UNAVAILABLE" : `p50 ${metric.p50.toFixed(4)} ${metric.unit ?? ""}`;
  if (!("valuePerNote" in metric) || metric.valuePerNote == null) return "UNAVAILABLE";
  return `${metric.valuePerNote.toFixed(2)} / note`;
}

export function EvaluationWorkspace() {
  const runs = useEvaluationRuns();
  const [selected, setSelected] = useState("");
  const detail = useEvaluationRun(selected);
  const summary = runs.data?.find((item) => item.evaluationRunId === selected);
  const metrics = detail.data?.aggregateMetrics ?? summary?.metrics ?? [];
  const metric = (id: string) => metrics.find((item) => item.metricId === id);

  return <>
    <WorkspaceHeader eyebrow="04 · EVALUATION" title="Measure reliability on synthetic scenarios" description="Metrics, denominators, provenance, latency, cost, burden, and failing cases are read from backend evaluation runs." />
    <StateCard title="Benchmark run">
      <select aria-label="Evaluation run" value={selected} onChange={(event) => setSelected(event.target.value)}>
        <option value="">Choose a saved run …</option>
        {runs.data?.map((item) => <option key={item.evaluationRunId} value={item.evaluationRunId}>{item.evaluationRunId} · {item.origin}</option>)}
      </select>
      {runs.isLoading && <p className="muted">Loading backend runs …</p>}
      {runs.error && <p className="error-banner" role="alert">Evaluation results are unavailable. Retry after the backend recovers.</p>}
      {runs.data?.length === 0 && <p className="muted">No evaluation runs are available. Metrics remain unavailable, not zero.</p>}
      {summary && <p className="muted">{summary.dataset?.datasetId ?? "Dataset unavailable"} · {summary.dataset?.datasetVersion ?? "version unavailable"} · provenance {summary.origin}</p>}
      {detail.isFetching && selected && <p className="muted">Loading immutable run detail …</p>}
    </StateCard>
    <div className="metric-grid">
      {metricIds.map(([id, label]) => { const selectedMetric = metric(id); const denominator = selectedMetric && "denominator" in selectedMetric ? selectedMetric.denominator : selectedMetric?.scorableCount; return <StateCard key={id} title={label}><strong>{metricValue(selectedMetric)}</strong><span>{selectedMetric?.reason ?? `Metric ${id}; denominator ${denominator ?? "unavailable"}`}</span></StateCard>; })}
    </div>
    {detail.data?.comparison && <StateCard title="Baseline versus validated"><p className="muted">Comparison status: {detail.data.comparison.status}. Baseline {detail.data.comparison.baselineRunId}; validated {detail.data.comparison.validatedRunId}.</p><ul>{detail.data.comparison.aggregateDeltas.map((delta, index) => <li key={index}>{String(delta.metricId ?? "metric")}: {String(delta.delta ?? "UNAVAILABLE")}</li>)}</ul></StateCard>}
    {detail.data && <StateCard title="Failing and inspected scenarios"><div className="finding-list">{detail.data.caseResults?.length ? detail.data.caseResults.map((item) => <div className="finding" key={item.caseExecutionId}><span>{item.scenarioId} · {item.candidateId}</span><strong>{item.status}</strong><p>{item.observedFindings.length} observed finding(s) · {item.matchResults.length} match result(s)</p></div>) : <p className="muted">No case results are available for this run.</p>}</div></StateCard>}
  </>;
}
