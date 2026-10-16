import { useEffect, useMemo, useState } from "react";
import { useEvaluationCase, useEvaluationRun, useEvaluationRuns, useRunEvaluation } from "../../api/hooks";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import type { EvaluationMetric } from "../../api/types";

const metricIds = [
  ["critical-error-recall", "Critical-error recall", "Of the serious planted errors, how many did the system catch?"],
  ["supported-claim-false-positive-rate", "False-positive rate", "How often did it flag a claim that was actually supported?"],
  ["claim-classification-accuracy", "Classification accuracy", "How often did it assign the right evidence outcome?"],
  ["completeness", "Completeness", "How much important source information made it into the note?"],
  ["scenario-level-detection", "Scenario detection", "How often were all serious errors in a scenario caught?"],
  ["final-note-remaining-errors", "Final-note quality", "How many annotated errors remained after review?"],
  ["review-burden-warnings", "Review burden", "How many warnings, decisions, and corrections did each note require?"],
  ["verification-latency", "Verification latency", "How long did automated verification take?"],
  ["additional-inference-cost", "Additional inference cost", "What did verification add per note?"],
] as const;
type CaseFilter = "ALL" | "MATCHED" | "FALSE_NEGATIVE" | "TARGET_LINKED_MISCLASSIFICATION" | "WARNINGS" | "FAILED";
const filters: [CaseFilter, string][] = [["ALL", "All cases"], ["MATCHED", "Caught correctly"], ["FALSE_NEGATIVE", "Missed"], ["TARGET_LINKED_MISCLASSIFICATION", "Misclassified"], ["WARNINGS", "Unexpected warnings"], ["FAILED", "Failed / unscorable"]];

function metricValue(metric: EvaluationMetric | undefined): string {
  if (!metric || metric.state !== "SCORED") return metric?.state ?? "UNAVAILABLE";
  if (metric.metricKind === "RATE") return metric.value == null ? "UNAVAILABLE" : `${(metric.value * 100).toFixed(1)}%`;
  if (metric.metricKind === "DURATION_DISTRIBUTION") { const formatMs = (value: number | null | undefined) => value == null ? "—" : value < 1 ? "<1" : value.toFixed(0); return metric.p50 == null ? "UNAVAILABLE" : `p50 ${formatMs(metric.p50)} ms · p95 ${formatMs(metric.p95)} ms`; }
  if (metric.metricKind === "COST_DISTRIBUTION") return metric.p50 == null ? "UNAVAILABLE" : `p50 ${metric.p50.toFixed(4)} ${metric.unit ?? ""}`;
  if (!("valuePerNote" in metric) || metric.valuePerNote == null) return "UNAVAILABLE";
  return `${metric.valuePerNote.toFixed(2)} / note`;
}
function metricContext(metric: EvaluationMetric | undefined): string {
  if (!metric) return "No result returned by the backend.";
  if (metric.state === "NOT_APPLICABLE") return `${metric.reason ?? "Not applicable"}. This is not a zero score.`;
  if (metric.state === "UNAVAILABLE") return `${metric.reason ?? "Unavailable"}. A required data source was not recorded.`;
  if ("numerator" in metric && "denominator" in metric) return `${metric.numerator} / ${metric.denominator} applicable items`;
  if ("observationCount" in metric) return `${metric.observationCount} recorded observations`;
  if ("count" in metric && "noteCount" in metric) return `${metric.count} total across ${metric.noteCount} notes`;
  return (metric as { reason?: string }).reason ?? "Backend-scored result";
}
function evidenceText(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "None recorded";
  return value.map((span) => { const item = span as Record<string, unknown>; return `${String(item.sourceId ?? "source")} v${String(item.sourceVersion ?? "?")} [${String(item.start ?? "? est.")}, ${String(item.end ?? "? est.")})`; }).join("; ");
}
function provenanceLabel(item: { origin?: string; evaluationEvidence?: string; historicalOrLive?: string; runStatus?: string }) {
  if (item.origin === "HISTORICAL_SAVED_RESULT") return { title: "Historical saved result", description: "Immutable result from an earlier run. It is not fresh inference." };
  if (item.evaluationEvidence === "SAVED_FIXTURE") return { title: "New saved-fixture replay", description: "A new run using saved synthetic fixture outputs; do not read this as live-model performance." };
  if (item.evaluationEvidence === "MOCKED_PROVIDER") return { title: "Mocked-provider test", description: "Deterministic test evidence, not a live model benchmark." };
  if (item.evaluationEvidence === "LIVE_MODEL") return { title: "Fresh live verification", description: "Newly executed against the configured live verifier on synthetic data." };
  return { title: item.historicalOrLive ?? "Evaluation result", description: `Run status: ${item.runStatus ?? "not reported"}.` };
}
function caseMatches(item: { status: string; matchResults: Array<{ disposition?: string }> }, filter: CaseFilter): boolean {
  if (filter === "ALL") return true;
  if (filter === "FAILED") return ["FAILED", "INVALID_OUTPUT", "UNSCORABLE", "SKIPPED"].includes(item.status);
  if (filter === "WARNINGS") return item.matchResults.some((m) => ["UNMATCHED_WARNING", "DUPLICATE"].includes(m.disposition ?? ""));
  return item.matchResults.some((m) => m.disposition === filter);
}

export function EvaluationWorkspace() {
  const runs = useEvaluationRuns();
  const [selected, setSelected] = useState("");
  const [selectedCase, setSelectedCase] = useState("");
  const [caseFilter, setCaseFilter] = useState<CaseFilter>("ALL");
  const runEvaluation = useRunEvaluation();
  useEffect(() => { if (!selected && runs.data?.[0]) setSelected(runs.data[0].evaluationRunId); }, [runs.data, selected]);
  const detail = useEvaluationRun(selected);
  const caseDetail = useEvaluationCase(selected, selectedCase);
  const summary = runs.data?.find((item) => item.evaluationRunId === selected);
  useEffect(() => { setSelectedCase(""); setCaseFilter("ALL"); }, [selected]);
  const metrics = detail.data?.aggregateMetrics ?? summary?.metrics ?? [];
  const cases = detail.data?.caseResults ?? [];
  const filteredCases = useMemo(() => cases.filter((item) => caseMatches(item, caseFilter)), [cases, caseFilter]);
  const provenance = provenanceLabel(summary ?? {});
  const runBenchmark = () => {
    const dataset = summary?.dataset;
    if (!dataset?.datasetId || !dataset.datasetVersion || !dataset.datasetHash) return;
    runEvaluation.mutate({ datasetId: dataset.datasetId, datasetVersion: dataset.datasetVersion, datasetHash: dataset.datasetHash, selectedSplit: (dataset.selectedSplit as "HELD_OUT" | "VALIDATION" | "DEVELOPMENT") ?? "HELD_OUT", executionMode: "SAVED_FIXTURE" }, { onSuccess: (run) => setSelected(run.evaluationRunId) });
  };
  const metric = (id: string) => metrics.find((item) => item.metricId === id);
  return <>
    <WorkspaceHeader eyebrow="03 · EVALUATION" title="Explainable benchmark dashboard" description="Understand what the synthetic benchmark caught, missed, and misclassified. Results are read from immutable backend evaluation runs." />
    <StateCard title="Choose a benchmark run" description="Saved replays and fresh verifier runs have different meanings. Check the provenance label before interpreting a metric.">
      <select aria-label="Evaluation run" value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Choose a saved run …</option>{runs.data?.map((item) => <option key={item.evaluationRunId} value={item.evaluationRunId}>{item.evaluationRunId} · {provenanceLabel(item).title}</option>)}</select>
      {summary && <div className="evaluation-provenance" role="status"><strong>{provenance.title}</strong><span>{provenance.description}</span></div>}
      {runs.isLoading && <p className="muted">Loading backend runs …</p>}{runs.error && <p className="error-banner" role="alert">Evaluation results are unavailable. Retry after the backend recovers.</p>}{runs.data?.length === 0 && <p className="muted">No evaluation runs are available. Metrics remain unavailable, not zero.</p>}
      {summary && <p className="muted">{summary.dataset?.datasetId ?? "Dataset unavailable"} · {summary.dataset?.datasetVersion ?? "version unavailable"} · split {summary.dataset?.selectedSplit ?? "not reported"}</p>}{summary && <p className="muted">Evidence: {summary.evaluationEvidence ?? summary.historicalOrLive ?? "backend result"} · annotation review: {summary.annotationReviewStatus ?? "not reported"}</p>}
      {detail.data?.configuration && <p className="muted">Verifier: {detail.data.configuration.modelProvider ?? "not reported"} · model: {detail.data.configuration.modelId ?? "not reported"} · version: {detail.data.configuration.modelVersion ?? "not reported"}</p>}
      <button type="button" aria-label="Run synthetic benchmark" onClick={runBenchmark} disabled={runEvaluation.isPending || !summary?.dataset?.datasetHash}>{runEvaluation.isPending ? "Replaying saved fixture …" : "Replay saved fixture"}</button>{runEvaluation.error && <p className="error-banner" role="alert">The benchmark could not be run. Existing evidence remains unchanged.</p>}{detail.isFetching && selected && <p className="muted">Loading immutable run detail …</p>}
    </StateCard>
    {summary && <StateCard title="Benchmark snapshot" description="A synthetic measurement of transcript fidelity—not a clinical-safety claim."><div className="evaluation-snapshot"><span><strong>{cases.length || "—"}</strong> cases in this run</span><span><strong>{summary.runStatus ?? "—"}</strong> run status</span><span><strong>{summary.annotationReviewStatus ?? "—"}</strong> annotation review</span><span><strong>{summary.evaluationEvidence ?? "—"}</strong> evidence source</span></div></StateCard>}
    <div className="metric-grid">{metricIds.map(([id, label, description]) => { const selectedMetric = metric(id); return <StateCard key={id} title={label} description={description}><strong>{metricValue(selectedMetric)}</strong><span>{metricContext(selectedMetric)}</span><details><summary>Metric details</summary><p className="muted">State: {selectedMetric?.state ?? "UNAVAILABLE"} · scorable: {selectedMetric?.scorableCount ?? "—"} · failed: {selectedMetric?.failedCount ?? "—"}</p></details></StateCard>; })}</div>
    {detail.data?.comparison && <StateCard title="Baseline versus validated" description="Automated finding comparison only; it does not infer caregiver improvement."><p className="muted">Status: {detail.data.comparison.status} · review data: {detail.data.comparison.reviewDataKind}. Baseline {detail.data.comparison.baselineRunId}; validated {detail.data.comparison.validatedRunId}.</p><ul>{detail.data.comparison.aggregateDeltas.map((delta, index) => <li key={index}>{String(delta.metricId ?? "metric")}: {String(delta.delta ?? "UNAVAILABLE")}</li>)}</ul></StateCard>}
    {detail.data && <StateCard title="Inspect cases" description="Select an outcome to see exactly why the benchmark counted it that way."><div className="evaluation-filters" role="group" aria-label="Filter evaluation cases">{filters.map(([value, label]) => <button type="button" key={value} className={caseFilter === value ? "selected" : ""} aria-pressed={caseFilter === value} onClick={() => setCaseFilter(value)}>{label} <span>({cases.filter((item) => caseMatches(item, value)).length})</span></button>)}</div><div className="finding-list">{filteredCases.length ? filteredCases.map((item) => <button type="button" className={`finding ${selectedCase === item.caseExecutionId ? "selected" : ""}`} key={item.caseExecutionId} onClick={() => setSelectedCase(item.caseExecutionId)} aria-label={`Inspect scenario ${item.scenarioId}`} aria-pressed={selectedCase === item.caseExecutionId}><span>{item.scenarioId} · {item.candidateId}</span><strong>{item.status}</strong><p>{item.observedFindings.length} observed finding(s) · {item.matchResults.length} match result(s)</p></button>) : <p className="muted">No cases match this outcome.</p>}</div></StateCard>}
    {selectedCase && caseDetail.isFetching && <StateCard title="Case inspection"><p className="muted">Loading transcript, note, and finding comparison …</p></StateCard>}{selectedCase && caseDetail.error && <StateCard title="Case inspection"><p className="error-banner" role="alert">This case inspection is unavailable. The saved run remains unchanged.</p></StateCard>}
    {caseDetail.data && <StateCard title={`Case inspection · ${caseDetail.data.scenarioId}`}><p className="muted">Status: {caseDetail.data.status} · execution {caseDetail.data.caseExecutionId}</p><div className="evaluation-text-compare"><section><h3>Source transcript <span className="text-label">AUTHORITATIVE SOURCE</span></h3><pre className="evaluation-source-text">{String(caseDetail.data.source.transcriptText ?? "Transcript unavailable")}</pre></section><section><h3>Generated candidate <span className="text-label">EVALUATED NOTE</span></h3><pre className="evaluation-candidate-text">{String(caseDetail.data.candidate.noteBody ?? "Note unavailable")}</pre></section></div><p className="muted">Candidate highlighting appears only when the backend supplies a validated note span.</p><details className="secondary-section"><summary>Expected findings</summary>{caseDetail.data.expectedFindings.length ? <ul>{caseDetail.data.expectedFindings.map((finding, index) => <li key={String(finding.errorId ?? index)}>{String(finding.severity ?? "severity unavailable")} · {String(finding.category ?? finding.errorType ?? "finding")} · {String(finding.description ?? finding.ruleId ?? "expected error")}<br />Evidence: {evidenceText(finding.sourceEvidenceSpans)}</li>)}</ul> : <p className="muted">No expected findings.</p>}</details><details className="secondary-section"><summary>Observed findings and matching decisions</summary>{caseDetail.data.actualFindings.length ? <ul>{caseDetail.data.actualFindings.map((finding, index) => <li key={String(finding.findingId ?? index)}>{String(finding.severity ?? "severity unavailable")} · {String(finding.status ?? "observed")} · {String(finding.discrepancy ?? finding.description ?? "finding")}<br />Evidence: {evidenceText(finding.sourceSpans)}</li>)}</ul> : <p className="muted">No actual findings.</p>}{caseDetail.data.disagreements.length ? <ul>{caseDetail.data.disagreements.map((item, index) => <li key={`${String(item.errorId ?? item.findingKey ?? "disagreement")}-${index}`}><strong>{String(item.dispositionLabel ?? item.disposition ?? "Disagreement")}</strong>: {String(item.explanation ?? item.reasonCode ?? "No explanation recorded.")}</li>)}</ul> : <p className="muted">No disagreements were recorded.</p>}</details><details className="secondary-section"><summary>Advanced: configuration and raw result</summary><p className="muted">Benchmark: {String(caseDetail.data.benchmark?.datasetId ?? "unavailable")} · version {String(caseDetail.data.benchmark?.datasetVersion ?? "unavailable")} · verifier {String(caseDetail.data.configuration.modelProvider ?? "unavailable")} / {String(caseDetail.data.configuration.modelId ?? "unavailable")} / {String(caseDetail.data.configuration.modelVersion ?? "unavailable")}</p><p className="muted">Latency: {String(caseDetail.data.latency?.totalMs ?? "unavailable")} ms · cost: {String(caseDetail.data.usageAndCost?.estimatedCost ?? "unavailable")}</p></details></StateCard>}
  </>;
}
