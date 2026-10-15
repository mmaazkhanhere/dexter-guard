import { useEffect, useState } from "react";
import { useEvaluationCase, useEvaluationRun, useEvaluationRuns, useRunEvaluation } from "../../api/hooks";
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

function evidenceText(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) return "None recorded";
  return value.map((span) => {
    if (!span || typeof span !== "object") return String(span);
    const item = span as Record<string, unknown>;
    return `${String(item.sourceId ?? "source")} v${String(item.sourceVersion ?? "?")} [${String(item.start ?? "?")}, ${String(item.end ?? "?")})`;
  }).join("; ");
}

export function EvaluationWorkspace() {
  const runs = useEvaluationRuns();
  const [selected, setSelected] = useState("");
  const [selectedCase, setSelectedCase] = useState("");
  const runEvaluation = useRunEvaluation();
  useEffect(() => { if (!selected && runs.data?.[0]) setSelected(runs.data[0].evaluationRunId); }, [runs.data, selected]);
  const detail = useEvaluationRun(selected);
  const caseDetail = useEvaluationCase(selected, selectedCase);
  const summary = runs.data?.find((item) => item.evaluationRunId === selected);
  useEffect(() => { setSelectedCase(""); }, [selected]);
  const metrics = detail.data?.aggregateMetrics ?? summary?.metrics ?? [];
  const metric = (id: string) => metrics.find((item) => item.metricId === id);
  const runBenchmark = () => {
    const dataset = summary?.dataset;
    if (!dataset?.datasetId || !dataset.datasetVersion || !dataset.datasetHash) return;
    runEvaluation.mutate({ datasetId: dataset.datasetId, datasetVersion: dataset.datasetVersion, datasetHash: dataset.datasetHash, selectedSplit: (dataset.selectedSplit as "HELD_OUT" | "VALIDATION" | "DEVELOPMENT") ?? "HELD_OUT", executionMode: "SAVED_FIXTURE" }, { onSuccess: (run) => setSelected(run.evaluationRunId) });
  };

  return <>
    <WorkspaceHeader eyebrow="03 · EVALUATION" title="Measure reliability on synthetic scenarios" description="Analyze benchmark cases, critical-error recall, false positives, latency, and verification performance from backend evaluation runs." />
    <StateCard title="Benchmark run">
      <select aria-label="Evaluation run" value={selected} onChange={(event) => setSelected(event.target.value)}>
        <option value="">Choose a saved run …</option>
        {runs.data?.map((item) => <option key={item.evaluationRunId} value={item.evaluationRunId}>{item.evaluationRunId} · {item.origin}</option>)}
      </select>
      {runs.isLoading && <p className="muted">Loading backend runs …</p>}
      {runs.error && <p className="error-banner" role="alert">Evaluation results are unavailable. Retry after the backend recovers.</p>}
      {runs.data?.length === 0 && <p className="muted">No evaluation runs are available. Metrics remain unavailable, not zero.</p>}
      {summary && <p className="muted">{summary.dataset?.datasetId ?? "Dataset unavailable"} · {summary.dataset?.datasetVersion ?? "version unavailable"} · provenance {summary.origin}</p>}
      {summary && <p className="muted">Evidence: {summary.evaluationEvidence ?? summary.historicalOrLive ?? "backend result"} · annotation review: {summary.annotationReviewStatus ?? "not reported"}</p>}
      {detail.data?.configuration && <p className="muted">Verifier: {detail.data.configuration.modelProvider ?? "not reported"} · model: {detail.data.configuration.modelId ?? "not reported"} · version: {detail.data.configuration.modelVersion ?? "not reported"}</p>}
      <button type="button" onClick={runBenchmark} disabled={runEvaluation.isPending || !summary?.dataset?.datasetHash}>{runEvaluation.isPending ? "Running benchmark …" : "Run synthetic benchmark"}</button>
      {runEvaluation.error && <p className="error-banner" role="alert">The benchmark could not be run. Existing evidence remains unchanged.</p>}
      {detail.isFetching && selected && <p className="muted">Loading immutable run detail …</p>}
    </StateCard>
    <div className="metric-grid">
      {metricIds.map(([id, label]) => { const selectedMetric = metric(id); const denominator = selectedMetric && "denominator" in selectedMetric ? selectedMetric.denominator : selectedMetric?.scorableCount; return <StateCard key={id} title={label}><strong>{metricValue(selectedMetric)}</strong><span>{selectedMetric?.reason ?? `Metric ${id}; denominator ${denominator ?? "unavailable"}`}</span></StateCard>; })}
    </div>
    {detail.data?.comparison && <StateCard title="Baseline versus validated"><p className="muted">Comparison status: {detail.data.comparison.status}. Baseline {detail.data.comparison.baselineRunId}; validated {detail.data.comparison.validatedRunId}.</p><ul>{detail.data.comparison.aggregateDeltas.map((delta, index) => <li key={index}>{String(delta.metricId ?? "metric")}: {String(delta.delta ?? "UNAVAILABLE")}</li>)}</ul></StateCard>}
    {detail.data && <StateCard title="Failing and inspected scenarios"><div className="finding-list">{detail.data.caseResults?.length ? detail.data.caseResults.map((item) => <button type="button" className="finding" key={item.caseExecutionId} onClick={() => setSelectedCase(item.caseExecutionId)} aria-label={`Inspect scenario ${item.scenarioId}`} aria-pressed={selectedCase === item.caseExecutionId}><span>{item.scenarioId} · {item.candidateId}</span><strong>{item.status}</strong><p>{item.observedFindings.length} observed finding(s) · {item.matchResults.length} match result(s)</p></button>) : <p className="muted">No case results are available for this run.</p>}</div></StateCard>}
    {selectedCase && caseDetail.isFetching && <StateCard title="Case inspection"><p className="muted">Loading transcript, note, and finding comparison …</p></StateCard>}
    {selectedCase && caseDetail.error && <StateCard title="Case inspection"><p className="error-banner" role="alert">This case inspection is unavailable. The saved run remains unchanged.</p></StateCard>}
    {caseDetail.data && <StateCard title={`Case inspection · ${caseDetail.data.scenarioId}`}><p className="muted">Status: {caseDetail.data.status} · execution {caseDetail.data.caseExecutionId}</p><p className="muted">Benchmark: {String(caseDetail.data.benchmark?.datasetId ?? "unavailable")} · version {String(caseDetail.data.benchmark?.datasetVersion ?? "unavailable")} · verifier {String(caseDetail.data.configuration.modelProvider ?? "unavailable")} / {String(caseDetail.data.configuration.modelId ?? "unavailable")} / {String(caseDetail.data.configuration.modelVersion ?? "unavailable")}</p><h3>Source transcript</h3><pre>{String(caseDetail.data.source.transcriptText ?? "Transcript unavailable")}</pre><h3>Generated note</h3><pre>{String(caseDetail.data.candidate.noteBody ?? "Note unavailable")}</pre><h3>Expected findings</h3>{caseDetail.data.expectedFindings.length ? <ul>{caseDetail.data.expectedFindings.map((finding, index) => <li key={String(finding.errorId ?? index)}>{String(finding.severity ?? "severity unavailable")} · {String(finding.category ?? finding.errorType ?? "finding")} · {String(finding.description ?? finding.ruleId ?? "expected error")}<br />Evidence: {evidenceText(finding.sourceEvidenceSpans)}</li>)}</ul> : <p className="muted">No expected findings.</p>}<h3>Actual findings</h3>{caseDetail.data.actualFindings.length ? <ul>{caseDetail.data.actualFindings.map((finding, index) => <li key={String(finding.findingId ?? index)}>{String(finding.severity ?? "severity unavailable")} · {String(finding.status ?? "observed")} · {String(finding.discrepancy ?? finding.description ?? "finding")}<br />Evidence: {evidenceText(finding.sourceSpans)}</li>)}</ul> : <p className="muted">No actual findings.</p>}<h3>Why this case passed or failed</h3>{caseDetail.data.disagreements.length ? <ul>{caseDetail.data.disagreements.map((item, index) => <li key={`${String(item.errorId ?? item.findingKey ?? "disagreement")}-${index}`}><strong>{String(item.dispositionLabel ?? item.disposition ?? "Disagreement")}</strong>: {String(item.explanation ?? item.reasonCode ?? "No explanation recorded.")}</li>)}</ul> : <p className="muted">No disagreements were recorded.</p>}<p className="muted">Latency: {String(caseDetail.data.latency?.totalMs ?? "unavailable")} ms · cost: {String(caseDetail.data.usageAndCost?.estimatedCost ?? "unavailable")}</p></StateCard>}
  </>;
}
