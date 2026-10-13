import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import { useState, type ReactNode } from "react";
import { useReview } from "../../api/hooks";
import { useWorkspace } from "../../state/workspace";
import type { Finding } from "../../api/types";

export function VerificationPage() {
  const { note, source } = useWorkspace();
  const review = useReview(note?.noteId, note?.revision);
  const [selected, setSelected] = useState<Finding>();
  const context = review.data;
  return <>
    <WorkspaceHeader eyebrow="02 · EVIDENCE VERIFICATION" title="Inspect claims against source evidence" description="Review backend-returned claims, findings, classifications, severities, and immutable evidence spans." />
    {!note && <div className="empty-state">Create or import a note in Documentation first.</div>}
    {note && <div className="workspace-grid evidence-grid">
      <StateCard title="Original German transcript"><EvidenceText text={context?.transcriptText ?? source?.transcript_text ?? ""} spans={selected?.evidence.spans ?? []} source={source} /></StateCard>
      <StateCard title="Candidate note"><p className="note-meta">Note {note.noteId} · revision {note.revision}</p><p className="evidence-note">{context?.candidateNote ?? note.content}</p></StateCard>
      <StateCard title="Findings"><div className="finding-list">{context?.findings.length ? context.findings.map((finding) => <button key={finding.reviewFindingId} className={selected?.reviewFindingId === finding.reviewFindingId ? "finding selected" : "finding"} onClick={() => setSelected(finding)}><span>{finding.reviewFindingId}</span><strong>{finding.upstreamStatus ?? "REVIEW FINDING"}</strong><em>{finding.severity}</em><p>{finding.explanation}</p></button>) : <p className="muted">No persisted findings for this revision. Verification may be unavailable until the backend verifier is configured.</p>}</div></StateCard>
      <StateCard title="Selected finding" tone={selected?.severity === "CRITICAL" ? "warning" : "neutral"}>{selected ? <><div className="finding-summary"><span className="status-label">{selected.upstreamStatus ?? "UNAVAILABLE"}</span><span className="status-label">Severity: {selected.severity}</span><span className="status-label">Provenance: {selected.origin}</span></div><p>{selected.explanation}</p><p className="muted">{selected.evidence.availability === "AVAILABLE" ? `${selected.evidence.spans.length} backend-provided source span(s)` : "Evidence unavailable or invalid; no source highlight is shown."}</p></> : <p className="muted">Select a finding to inspect its source-bound evidence.</p>}</StateCard>
    </div>}
  </>;
}

function EvidenceText({ text, spans, source }: { text: string; spans: Finding["evidence"]["spans"]; source?: { source_id: string; source_version: number } }) {
  if (!text) return <p className="muted">Source unavailable.</p>;
  const valid = spans.filter((span) => span.sourceId === source?.source_id && span.sourceVersion === source?.source_version && span.start >= 0 && span.end > span.start && span.end <= Array.from(text).length).sort((a, b) => a.start - b.start);
  if (!valid.length) return <p className="evidence-note">{text}</p>;
  const codePoints = Array.from(text); const chunks: ReactNode[] = []; let cursor = 0;
  valid.forEach((span, index) => { if (span.start < cursor) return; if (span.start > cursor) chunks.push(<span key={`plain-${index}`}>{codePoints.slice(cursor, span.start).join("")}</span>); chunks.push(<mark key={`evidence-${index}`}>{codePoints.slice(span.start, span.end).join("")}</mark>); cursor = span.end; });
  chunks.push(<span key="tail">{codePoints.slice(cursor).join("")}</span>);
  return <p className="evidence-note">{chunks}</p>;
}
