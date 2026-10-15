import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import { useEffect, useState } from "react";
import { useApprove, useFindingDecision, useFullVerification, useReject, useReview, useSaveRevision, safeMutationError } from "../../api/hooks";
import { userFacingFailureMessage } from "../../api/errors";
import { useWorkspace } from "../../state/workspace";

export function ReviewPage() {
  const { note, draftContent, setDraftContent, applyNoteRevision } = useWorkspace();
  const review = useReview(note?.noteId, note?.revision);
  const save = useSaveRevision(); const verify = useFullVerification(); const decide = useFindingDecision(); const approve = useApprove(); const reject = useReject();
  const [content, setContent] = useState(draftContent ?? note?.content ?? ""); const [reviewer, setReviewer] = useState("synthetic-reviewer"); const [reason, setReason] = useState("");
  useEffect(() => { const next = draftContent ?? review.data?.candidateNote ?? note?.content ?? ""; setContent(next); }, [draftContent, review.data?.candidateNote, note?.content]);
  const context = review.data;
  const hasUnsavedChanges = Boolean(note && content !== note.content);
  async function saveRevision() { if (!note || !content.trim() || !hasUnsavedChanges) return; const result = await save.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, content, reviewerLabel: reviewer }); applyNoteRevision({ ...note, revision: result.revision, content }); setDraftContent(content); await review.refetch(); }
  async function fullVerify() { if (!note || hasUnsavedChanges) return; await verify.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, reviewerLabel: reviewer }); await review.refetch(); }
  return <>
    <WorkspaceHeader eyebrow="03 · HUMAN REVIEW" title="Resolve findings and approve safely" description="Edits create successor revisions. Approval remains controlled by the backend's latest complete-note verification." />
    {!note && <div className="empty-state">Create or import a note in Documentation first.</div>}
    {note && <>
      {(save.error || verify.error || decide.error || approve.error || reject.error) && <div className="error-banner" role="alert">{safeMutationError(save.error ?? verify.error ?? decide.error ?? approve.error ?? reject.error).message}</div>}
      <div className="workspace-grid">
        <StateCard title={`Current persisted revision · ${note.revision}`}><label>Reviewer label<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label><textarea aria-label="Editable nursing note" value={content} onChange={(event) => setContent(event.target.value)} /><div className="button-row"><button onClick={saveRevision} disabled={save.isPending || !hasUnsavedChanges}>{save.isPending ? "Saving …" : "Save successor revision"}</button><button className="secondary-button" onClick={fullVerify} disabled={verify.isPending || save.isPending || hasUnsavedChanges} aria-describedby={hasUnsavedChanges ? "verification-save-required" : undefined}>{verify.isPending ? "Verifying …" : "Run full verification"}</button></div><p id="verification-save-required" className="muted">{hasUnsavedChanges ? "Save the edited note as a new revision before running full verification." : "Full verification runs against this exact saved note revision. Saving creates an immutable successor."}</p></StateCard>
      <StateCard title="Approval eligibility" tone={context?.approvalEligible && !hasUnsavedChanges ? "neutral" : "warning"}><div className="eligibility">{context?.approvalEligible && !hasUnsavedChanges ? "Ready for approval" : "Not ready for approval"}</div><p>{hasUnsavedChanges ? "Unsaved changes must be saved as a new revision and verified before approval." : context?.fullVerification ? (context.fullVerification.status === "VALID" ? "The note passed the current verification checks." : "The note still needs attention.") : "A complete verification is required before approval."}</p>{context?.fullVerification?.failureMessage && <p className="muted">{userFacingFailureMessage(context.fullVerification.failureCode, context.fullVerification.failureMessage)}</p>}<div className="button-row"><button onClick={() => context?.fullVerification && !hasUnsavedChanges && context.approvalEligible && approve.mutate({ noteId: note.noteId, expectedRevision: note.revision, fullVerificationId: context.fullVerification.fullVerificationId, reviewerLabel: reviewer })} disabled={!context?.approvalEligible || hasUnsavedChanges || approve.isPending}>Approve</button><button className="danger-button" onClick={() => reject.mutate({ noteId: note.noteId, expectedRevision: note.revision, reviewerLabel: reviewer, reason })} disabled={reject.isPending || reason.trim().length < 3}>Reject</button></div><label>Rejection reason<input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Required for rejection" /></label></StateCard>
        <StateCard title="Finding decisions"><div className="finding-list">{context?.findings.length ? context.findings.map((finding) => <div className="finding" key={finding.reviewFindingId}><span>{finding.reviewFindingId}</span><strong>{finding.state}</strong><p>{finding.explanation}</p><div className="button-row"><button className="secondary-button" onClick={() => decide.mutate({ noteId: note.noteId, findingId: finding.reviewFindingId, expectedRevision: note.revision, kind: "ACKNOWLEDGED", reviewerLabel: reviewer })}>Acknowledge</button><button className="secondary-button" onClick={() => decide.mutate({ noteId: note.noteId, findingId: finding.reviewFindingId, expectedRevision: note.revision, kind: "DISPUTED", reviewerLabel: reviewer, rationale: "Reviewer dispute recorded." })}>Dispute</button></div></div>) : <p className="muted">No findings loaded for this revision.</p>}</div></StateCard>
      </div>
    </>}
  </>;
}
