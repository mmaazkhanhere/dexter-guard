import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import { LoadingIndicator } from "../../components/shared/LoadingIndicator";
import { userFacingFailureMessage } from "../../api/errors";
import { useEffect, useState, type ReactNode } from "react";
import { useReview } from "../../api/hooks";
import { useWorkspace } from "../../state/workspace";
import type { Finding, NoteResponse, ReviewContext, SourceDocument } from "../../api/types";
import { nonOverlappingSpans, validSourceSpans } from "./spans";

export function VerificationPage() {
  const { note, source } = useWorkspace();
  const review = useReview(note?.noteId, note?.revision);
  const context = review.data;
  return <>
    <WorkspaceHeader eyebrow="02 · EVIDENCE VERIFICATION" title="Inspect claims against source evidence" description="Review backend-returned claims, findings, classifications, severities, and immutable evidence spans." />
    {!note && <div className="empty-state">Create or import a note in Documentation first.</div>}
    {note && <VerificationResults note={note} source={source} context={context} isLoading={review.isLoading || review.isFetching} />}
    {/*
      <StateCard title="Original German transcript"><EvidenceText text={context?.transcriptText ?? source?.transcript_text ?? ""} spans={selected?.evidence.spans ?? []} source={source} /></StateCard>
      <StateCard title="Candidate note"><p className="note-meta">Note {note.noteId} · revision {note.revision}</p><p className="evidence-note">{context?.candidateNote ?? note.content}</p></StateCard>
      <StateCard title="Findings"><div className="finding-list">{context?.findings.length ? context.findings.map((finding) => <button key={finding.reviewFindingId} className={selected?.reviewFindingId === finding.reviewFindingId ? "finding selected" : "finding"} onClick={() => setSelected(finding)}><span>{finding.reviewFindingId}</span><strong>{finding.upstreamStatus ?? "REVIEW FINDING"}</strong><em>{finding.severity}</em><p>{finding.explanation}</p></button>) : <p className="muted">No persisted findings for this revision. Verification may be unavailable until the backend verifier is configured.</p>}</div></StateCard>
      <StateCard title="Selected finding" tone={selected?.severity === "CRITICAL" ? "warning" : "neutral"}>{selected ? <div id="selected-finding" tabIndex={-1}><div className="finding-summary"><span className="status-label">Classification: {selected.upstreamStatus ?? "UNAVAILABLE"}</span><span className="status-label">Severity: {selected.severity}</span><span className="status-label">Provenance: {selected.origin}</span></div><p>{selected.explanation}</p><p className="muted">{selected.evidence.availability === "AVAILABLE" ? `${selected.evidence.spans.length} backend-provided source span(s)` : "Evidence unavailable or invalid; no source highlight is shown."}</p></div> : <p className="muted">Select a finding to inspect its source-bound evidence.</p>}</StateCard>
    */}
  </>;
}

type VerificationResultsProps = { note: NoteResponse; source?: SourceDocument; context?: ReviewContext; isLoading?: boolean };

export function VerificationResults({ note, source, context, isLoading = false }: VerificationResultsProps) {
  const [selected, setSelected] = useState<Finding>();
  useEffect(() => {
    if (selected) document.getElementById("selected-finding")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selected]);
  const fullVerification = context?.fullVerification;
  const verification = fullVerification?.noteRevision === note.revision ? fullVerification : undefined;
  const findings = context?.findings ?? [];
  const approvalEligible = verification?.status === "VALID" && context?.approvalEligible === true;
  return <>
    {isLoading && <div className="empty-state" role="status"><LoadingIndicator label="Checking the nursing note against the transcript …" /></div>}
    {verification && <div className={verification.status === "VALID" ? (approvalEligible ? "status-banner" : "warning-banner") : "error-banner"} role="status">{verification.status !== "VALID" ? `Verification did not complete successfully. ${userFacingFailureMessage(verification.failureCode, verification.failureMessage)}` : approvalEligible ? "Verification completed with no blocking findings. The note is ready for human approval." : "Verification completed. Review the findings before approval; the note is not yet eligible for approval."}</div>}
    <div className="workspace-grid evidence-grid">
      <StateCard title="Locked source transcript"><EvidenceText text={context?.transcriptText ?? source?.transcript_text ?? ""} spans={selected?.evidence.spans ?? []} source={source} /></StateCard>
      <StateCard title="Read-only candidate note"><p className="note-meta">Note {note.noteId} · revision {note.revision}</p><NoteText text={context?.candidateNote ?? note.content} span={selected?.claimSpan ?? undefined} /></StateCard>
      <StateCard title="Verification findings"><div className="finding-list">{findings.length ? findings.map((finding) => <button key={finding.reviewFindingId} className={selected?.reviewFindingId === finding.reviewFindingId ? "finding selected" : "finding"} onClick={() => setSelected(finding)}><span>{finding.reviewFindingId}</span><strong>{finding.upstreamStatus ?? "REVIEW FINDING"}</strong><em>{finding.severity}</em><p>{finding.explanation}</p></button>) : <p className="muted">{verification ? "No persisted findings were returned for this verification." : "Verification results are not available yet."}</p>}</div></StateCard>
      <StateCard title="Selected finding" tone={selected?.severity === "CRITICAL" ? "warning" : "neutral"}>{selected ? <div id="selected-finding" tabIndex={-1}><div className="finding-summary"><span className="status-label">Classification: {selected.upstreamStatus ?? "UNAVAILABLE"}</span><span className="status-label">Severity: {selected.severity}</span><span className="status-label">Provenance: {selected.origin}</span></div><p>{selected.explanation}</p><p className="muted">{selected.evidence.availability === "AVAILABLE" ? `${selected.evidence.spans.length} backend-provided source span(s); the affected note span is highlighted when available.` : "Evidence unavailable or invalid; no source highlight is shown."}</p></div> : <p className="muted">Select a finding to inspect its highlighted note text and source-bound evidence.</p>}</StateCard>
    </div>
  </>;
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
