import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import { LoadingIndicator } from "../../components/shared/LoadingIndicator";
import { userFacingFailureMessage } from "../../api/errors";
import { useEffect, useState, type ReactNode } from "react";
import { useReview } from "../../api/hooks";
import { useWorkspace } from "../../state/workspace";
import type { Finding, NoteResponse, ReviewContext, SourceDocument } from "../../api/types";
import { isFindingUnresolved } from "../review/findings";
import { nonOverlappingSpans, projectSourceSpan, validSourceSpans } from "./spans";

export function VerificationPage() {
  const { note, source } = useWorkspace();
  const review = useReview(note?.noteId, note?.revision);
  const context = review.data;
  return <>
    <WorkspaceHeader eyebrow="02 · EVIDENCE VERIFICATION" title="Inspect claims against source evidence" description="Review backend-returned claims, findings, classifications, severities, and immutable evidence spans." />
    {!note && <div className="empty-state">Create or import a note in Documentation first.</div>}
    {note && <VerificationResults note={note} source={source} context={context} isLoading={review.isLoading || review.isFetching} loadError={review.error} onRetry={() => { void review.refetch(); }} />}
    {/*
      <StateCard title="Original German transcript"><EvidenceText text={context?.transcriptText ?? source?.transcript_text ?? ""} spans={selected?.evidence.spans ?? []} source={source} /></StateCard>
      <StateCard title="Candidate note"><p className="note-meta">Note {note.noteId} · revision {note.revision}</p><p className="evidence-note">{context?.candidateNote ?? note.content}</p></StateCard>
      <StateCard title="Findings"><div className="finding-list">{context?.findings.length ? context.findings.map((finding) => <button key={finding.reviewFindingId} className={selected?.reviewFindingId === finding.reviewFindingId ? "finding selected" : "finding"} onClick={() => setSelected(finding)}><span>{finding.reviewFindingId}</span><strong>{finding.upstreamStatus ?? "REVIEW FINDING"}</strong><em>{finding.severity}</em><p>{finding.explanation}</p></button>) : <p className="muted">No persisted findings for this revision. Verification may be unavailable until the backend verifier is configured.</p>}</div></StateCard>
      <StateCard title="Selected finding" tone={selected?.severity === "CRITICAL" ? "warning" : "neutral"}>{selected ? <div id="selected-finding" tabIndex={-1}><div className="finding-summary"><span className="status-label">Classification: {selected.upstreamStatus ?? "UNAVAILABLE"}</span><span className="status-label">Severity: {selected.severity}</span><span className="status-label">Provenance: {selected.origin}</span></div><p>{selected.explanation}</p><p className="muted">{selected.evidence.availability === "AVAILABLE" ? `${selected.evidence.spans.length} backend-provided source span(s)` : "Evidence unavailable or invalid; no source highlight is shown."}</p></div> : <p className="muted">Select a finding to inspect its source-bound evidence.</p>}</StateCard>
    */}
  </>;
}

type VerificationResultsProps = { note: NoteResponse; source?: SourceDocument; context?: ReviewContext; isLoading?: boolean; loadError?: unknown; onRetry?: () => void };

export function VerificationResults({ note, source, context, isLoading = false, loadError, onRetry }: VerificationResultsProps) {
  const [selected, setSelected] = useState<Finding>();
  useEffect(() => {
    if (selected) document.getElementById("selected-finding")?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [selected]);
  const fullVerification = context?.fullVerification;
  const verification = fullVerification?.noteRevision === note.revision ? fullVerification : undefined;
  const findings = context?.findings ?? [];
  const orderedFindings = [...findings].sort((left, right) => severityRank(left.severity) - severityRank(right.severity) || unresolvedRank(left.state) - unresolvedRank(right.state));
  const unresolved = findings.filter((finding) => isFindingUnresolved(finding, context?.decisions ?? []));
  const unresolvedFindings = unresolved.length;
  const approvalEligible = !isLoading && !loadError && verification?.status === "VALID" && context?.approvalEligible === true && unresolvedFindings === 0;
  const criticalFindings = findings.filter((finding) => finding.severity === "CRITICAL").length;
  const majorFindings = findings.filter((finding) => finding.severity === "MAJOR").length;
  const unresolvedSeveritySummary = formatSeverityCounts(unresolved);
  const sourceText = context?.transcriptText ?? source?.transcript_text ?? "";
  const verificationReady = Boolean(verification && !loadError && !isLoading && verification.status === "VALID");
  return <>
    {isLoading && <div className="empty-state" role="status"><LoadingIndicator label="Checking the nursing note against the transcript …" /></div>}
    {loadError && <div className="error-banner" role="alert"><strong>Verification results could not be loaded. Approval blocked.</strong><div className="button-row"><button type="button" className="secondary-button" onClick={onRetry} disabled={!onRetry || isLoading}>{isLoading ? "Retrying …" : "Retry loading results"}</button></div></div>}
    {verification && !loadError && verification.status !== "VALID" && <div className="error-banner" role="alert"><strong>Verification failed. Approval blocked.</strong> {userFacingFailureMessage(verification.failureCode, verification.failureMessage)}</div>}
    {verificationReady && approvalEligible && <div className="status-banner" role="status"><strong>{findings.length === 0 ? "No findings were recorded." : "All recorded findings have been resolved or adjudicated."}</strong> Human approval required.</div>}
    {verificationReady && !approvalEligible && unresolvedFindings === 0 && <div className="warning-banner" role="status"><strong>Review required.</strong> Verification completed, but approval eligibility is not confirmed. Inspect the recorded findings and complete Human Review.</div>}
    {verificationReady && unresolvedFindings > 0 && <div className="warning-banner" role="status"><strong>Review required.</strong> {unresolvedFindings} unresolved {unresolvedFindings === 1 ? "issue" : "issues"}: {unresolvedSeveritySummary}. Approval blocked until the issues are resolved or adjudicated.</div>}
    {verification && <section className="verification-overview" aria-label="Verification overview">
      <div className="verification-summary" aria-label="Finding summary">
        <div><span>Total findings</span><strong>{findings.length}</strong></div>
        <div><span>Critical</span><strong>{criticalFindings}</strong></div>
        <div><span>Major</span><strong>{majorFindings}</strong></div>
        <div><span>Unresolved</span><strong>{unresolvedFindings}</strong></div>
      </div>
      <div className={approvalEligible ? "eligibility-callout eligible" : "eligibility-callout"} role="status">
        <strong>Approval eligibility: {approvalEligible ? "Eligible" : "Not eligible"}</strong>
        <p>{approvalEligible ? "A human reviewer must still approve the note." : unresolvedFindings ? "Caregiver action: resolve the prioritized findings in Human Review, save a new revision, and run full verification again." : "Caregiver action: inspect the findings and complete the Human Review approval workflow."}</p>
      </div>
    </section>}
    <div className="workspace-grid evidence-grid">
      <StateCard title="Locked source transcript"><EvidenceText text={sourceText} spans={selected?.evidence.spans ?? []} source={source} /></StateCard>
      <StateCard title="Read-only candidate note"><p className="note-meta">Note {note.noteId} · revision {note.revision}</p><NoteText text={context?.candidateNote ?? note.content} span={selected?.claimSpan ?? undefined} /></StateCard>
      <StateCard title="Verification findings"><div className="finding-list">{orderedFindings.length ? orderedFindings.map((finding) => <button key={finding.reviewFindingId} className={selected?.reviewFindingId === finding.reviewFindingId ? "finding selected" : "finding"} onClick={() => setSelected(finding)}><span>{finding.reviewFindingId}</span><strong>{classificationLabel(finding.upstreamStatus)}</strong><em>{finding.severity}</em><p>{finding.explanation}</p><p className="finding-evidence-preview">Source evidence: {sourceEvidencePreview(finding, sourceText) ?? "Unavailable or invalid; no source excerpt is shown."}</p></button>) : <p className="muted">{verification ? "No persisted findings were returned for this verification." : "Verification results are not available yet."}</p>}</div></StateCard>
      <StateCard title="Selected finding" tone={selected?.severity === "CRITICAL" ? "warning" : "neutral"}>{selected ? <div id="selected-finding" tabIndex={-1}><div className="finding-summary"><span className="status-label">Classification: {classificationLabel(selected.upstreamStatus)}</span><span className="status-label">Severity: {selected.severity}</span><span className="status-label">Provenance: {selected.origin}</span></div><p>{selected.explanation}</p><h4>Problematic note text</h4><div className="evidence-note">{selected.claimSpan ? <NoteText text={context?.candidateNote ?? note.content} span={selected.claimSpan} /> : "No valid candidate-note span is available for this finding."}</div><h4>Corresponding source evidence</h4><p className="evidence-note">{sourceEvidencePreview(selected, sourceText) ?? "Evidence is unavailable or invalid; no source highlight is shown."}</p><details><summary>Technical details</summary><dl className="technical-details"><dt>Finding</dt><dd>{selected.reviewFindingId}</dd><dt>Rule</dt><dd>{selected.ruleCode ?? "Not supplied"}</dd><dt>Source</dt><dd>{selected.sourceId} · version {selected.sourceVersion}</dd><dt>Severity rationale</dt><dd>{selected.severityRationale}</dd></dl></details></div> : <p className="muted">Select a finding to inspect its highlighted note text and source-bound evidence.</p>}</StateCard>
    </div>
  </>;
}

function severityRank(severity: Finding["severity"]): number { return severity === "CRITICAL" ? 0 : severity === "MAJOR" ? 1 : 2; }
function unresolvedRank(state: Finding["state"]): number { return state === "OPEN" || state === "STALE" ? 0 : 1; }
function formatSeverityCounts(findings: Finding[]): string {
  const counts = { CRITICAL: 0, MAJOR: 0, MINOR: 0 };
  findings.forEach((finding) => { counts[finding.severity] += 1; });
  return (["CRITICAL", "MAJOR", "MINOR"] as const)
    .filter((severity) => counts[severity] > 0)
    .map((severity) => `${counts[severity]} ${severity.toLowerCase()}`)
    .join(", ");
}
function classificationLabel(status?: string | null): string {
  const normalized = status?.toUpperCase();
  if (normalized === "SUPPORTED") return "Supported";
  if (normalized === "UNSUPPORTED") return "Unsupported";
  if (normalized === "CONTRADICTED") return "Contradicted";
  if (normalized === "UNCERTAIN") return "Uncertain";
  return "Classification unavailable";
}
function sourceEvidencePreview(finding: Finding, transcript: string): string | undefined {
  if (!transcript || finding.evidence.availability !== "AVAILABLE") return undefined;
  const spans = nonOverlappingSpans(validSourceSpans(transcript, finding.sourceId, finding.sourceVersion, finding.evidence.spans));
  const excerpts = spans.map((span) => projectSourceSpan(transcript, span)).filter((excerpt): excerpt is string => Boolean(excerpt));
  return excerpts.length ? excerpts.join(" … ") : undefined;
}

function EvidenceText({ text, spans, source }: { text: string; spans: Finding["evidence"]["spans"]; source?: { source_id: string; source_version: number } }) {
  if (!text) return <p className="muted">Source unavailable.</p>;
  const valid = source ? nonOverlappingSpans(validSourceSpans(text, source.source_id, source.source_version, spans)) : [];
  if (!valid.length) return <p className="evidence-note">{text}</p>;
  const codePoints = Array.from(text); const chunks: ReactNode[] = []; let cursor = 0;
  valid.forEach((span, index) => { if (span.start < cursor) return; if (span.start > cursor) chunks.push(<span key={`plain-${index}`}>{codePoints.slice(cursor, span.start).join("")}</span>); chunks.push(<mark key={`evidence-${index}`}>{codePoints.slice(span.start, span.end).join("")}</mark>); cursor = span.end; });
  chunks.push(<span key="tail">{codePoints.slice(cursor).join("")}</span>);
  return <p className="evidence-note">{chunks}</p>;
}

function NoteText({ text, span }: { text: string; span?: Finding["claimSpan"] }) {
  if (!span) return <p className="evidence-note">{text}</p>;
  const codePoints = Array.from(text);
  if (span.startCodePoint < 0 || span.endCodePointExclusive <= span.startCodePoint || span.endCodePointExclusive > codePoints.length) return <p className="evidence-note">{text}</p>;
  return <p className="evidence-note">{codePoints.slice(0, span.startCodePoint).join("")}<mark>{codePoints.slice(span.startCodePoint, span.endCodePointExclusive).join("")}</mark>{codePoints.slice(span.endCodePointExclusive).join("")}</p>;
}
