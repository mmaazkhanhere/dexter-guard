import { useState } from "react";
import { useEvaluationRuns } from "../../api/hooks";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";

export function EvaluationDashboard() {
  const runs = useEvaluationRuns();
  const [selected, setSelected] = useState("");
  const run = runs.data?.find((item) => item.evaluationRunId === selected);
  const metric = (names: string[]) => run?.aggregateMetrics?.find((item) => names.includes(item.metricName));
  const display = (names: string[]) => { const item = metric(names); if (!item || item.state !== "SCORED" || item.value === undefined) return "UNAVAILABLE"; return `${(item.value * 100).toFixed(1)}%`; };
  return <><WorkspaceHeader eyebrow="04 · EVALUATION" title="Measure reliability on synthetic scenarios" description="Metrics, denominators, provenance, latency, cost, burden, and failing cases are read from backend evaluation runs." /><StateCard title="Benchmark run"><select aria-label="Evaluation run" value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Choose a saved run …</option>{runs.data?.map((item) => <option key={item.evaluationRunId} value={item.evaluationRunId}>{item.evaluationRunId} · {item.origin}</option>)}</select>{runs.isLoading && <p className="muted">Loading backend runs …</p>}{runs.data?.length === 0 && <p className="muted">No evaluation runs are available. Metrics remain unavailable, not zero.</p>}{run && <p className="muted">{run.datasetId} · dataset {run.datasetVersion} · provenance {run.origin}</p>}</StateCard><div className="metric-grid"><StateCard title="Critical-error recall"><strong>{display(["CRITICAL_ERROR_RECALL"])}</strong><span>Backend MetricResult</span></StateCard><StateCard title="Classification accuracy"><strong>{display(["CLAIM_CLASSIFICATION_ACCURACY"])}</strong><span>Denominator retained by backend</span></StateCard><StateCard title="Completeness"><strong>{display(["COMPLETENESS"])}</strong><span>Source-to-note coverage</span></StateCard></div></>;
}
