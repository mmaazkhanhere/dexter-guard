import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";

export function EvaluationPage() {
  return <><WorkspaceHeader eyebrow="04 · EVALUATION" title="Measure reliability on synthetic scenarios" description="Metrics, denominators, provenance, latency, cost, and failing cases are read from backend evaluation runs." /><div className="metric-grid"><StateCard title="Critical-error recall"><strong>UNAVAILABLE</strong><span> No run selected</span></StateCard><StateCard title="Classification accuracy"><strong>UNAVAILABLE</strong><span> No run selected</span></StateCard><StateCard title="Verification latency"><strong>UNAVAILABLE</strong><span> p50 / p95</span></StateCard></div></>;
}
