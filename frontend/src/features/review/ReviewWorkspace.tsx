import { useEffect, useState } from "react";
import { safeMutationError, useApprove, useAudit, useFindingDecision, useFullVerification, useReject, useReview, useSaveRevision } from "../../api/hooks";
import { userFacingFailureMessage } from "../../api/errors";
import { StateCard } from "../../components/shared/StateCard";
import { useToast } from "../../components/shared/Toaster";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { useWorkspace } from "../../state/workspace";

export function ReviewWorkspace() {
  const { note: noteMaybe, draftContent, setDraftContent, applyNoteRevision } = useWorkspace();
  const { notify } = useToast();
  const note = noteMaybe!;
  const review = useReview(noteMaybe?.noteId, noteMaybe?.revision);
  const audit = useAudit(noteMaybe?.noteId);
  const save = useSaveRevision();
  const verify = useFullVerification();
  const decide = useFindingDecision();
  const approve = useApprove();
  const reject = useReject();
  const [content, setContent] = useState(draftContent ?? noteMaybe?.content ?? "");
  const [reviewer, setReviewer] = useState("synthetic-reviewer");
  const [reason, setReason] = useState("");

  useEffect(() => {
    setContent(draftContent ?? review.data?.candidateNote ?? noteMaybe?.content ?? "");
  }, [draftContent, review.data?.candidateNote, noteMaybe?.content]);

  if (!note) return <><WorkspaceHeader eyebrow="03 · HUMAN REVIEW" title="Resolve findings and approve safely" description="Edits create successor revisions. Approval remains controlled by the backend's latest complete-note verification." /><div className="empty-state">Create or import a note in Documentation first.</div></>;

  const context = review.data;
  const currentVerification = context?.fullVerification?.noteRevision === note.revision ? context.fullVerification : undefined;
  const staleContext = Boolean(context && context.latestRevision > note.revision);
  const approvalEligible = Boolean(context?.approvalEligible && currentVerification?.status === "VALID" && !verify.isPending && !save.isPending);
  const firstError = save.error ?? verify.error ?? decide.error ?? approve.error ?? reject.error;

  async function saveRevision() {
    if (!content.trim() || content === note.content) return;
    try {
      const result = await save.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, content, reviewerLabel: reviewer });
      applyNoteRevision({ ...note, revision: result.revision, content });
      setDraftContent(content);
      await review.refetch();
      notify({ tone: "success", title: "New version saved", message: "Your changes were saved as a new note version. Check it again before approval." });
    } catch (actionError) {
      notifyFailure(notify, "Revision was not saved", actionError, "The current persisted revision was not changed.");
    }
  }

  async function fullVerify() {
    try {
      const result = await verify.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, reviewerLabel: reviewer });
      await review.refetch();
      if (result.status === "VALID") {
        notify({ tone: "success", title: "Note checked", message: "The note passed the current checks. Review the findings before approving it." });
      } else {
        notify({ tone: "error", title: "The note needs attention", message: `${userFacingFailureMessage(result.failureCode, result.failureMessage)} Approval remains unavailable until the issues are resolved.` });
      }
    } catch (actionError) {
      notifyFailure(notify, "Full verification could not run", actionError, "The note remains in its prior verification state and approval eligibility was not changed.");
    }
  }

  async function suggestionDecision(findingId: string, suggestionId: string, kind: "SUGGESTION_ACCEPTED" | "SUGGESTION_REJECTED") {
    if (kind === "SUGGESTION_REJECTED" && reason.trim().length < 3) return;
    await recordDecision(findingId, kind, suggestionId);
  }

  async function recordDecision(findingId: string, kind: "ACKNOWLEDGED" | "DISPUTED" | "SUGGESTION_ACCEPTED" | "SUGGESTION_REJECTED", suggestionId?: string) {
    try {
      const result = await decide.mutateAsync({ noteId: note.noteId, findingId, expectedRevision: note.revision, kind, suggestionId, reviewerLabel: reviewer, rationale: kind === "DISPUTED" || kind === "SUGGESTION_REJECTED" ? reason : undefined });
      const refreshed = await review.refetch();
      if (result.successorRevision && refreshed.data?.candidateNote) applyNoteRevision({ ...note, revision: result.successorRevision, content: refreshed.data.candidateNote });
      const revisionDetail = result.successorRevision ? " A new version was created and must be checked again before approval." : "";
      notify({ tone: "success", title: "Decision saved", message: `Your decision was saved.${revisionDetail}` });
    } catch (actionError) {
      notifyFailure(notify, "Finding decision was not recorded", actionError, "The finding and note revision were not changed.");
    }
  }

  async function approveNote() {
    if (!currentVerification) return;
    try {
      await approve.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, fullVerificationId: currentVerification.fullVerificationId, reviewerLabel: reviewer });
      await review.refetch();
      notify({ tone: "success", title: "Note approved", message: "The note was approved and recorded." });
    } catch (actionError) {
      notifyFailure(notify, "Note was not approved", actionError, "The backend did not record an approval; review the current eligibility and verification state.");
    }
  }

  async function rejectNote() {
    try {
      await reject.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, reviewerLabel: reviewer, reason });
      await review.refetch();
      notify({ tone: "success", title: "Note rejected", message: "The note was rejected and recorded." });
    } catch (actionError) {
      notifyFailure(notify, "Note was not rejected", actionError, "The backend did not record a rejection; the current disposition was not changed.");
    }
  }

  return <>
    <WorkspaceHeader eyebrow="03 · HUMAN REVIEW" title="Resolve findings and approve safely" description="Edits create successor revisions. Approval remains controlled by the backend's latest complete-note verification." />
    {firstError && <div className="error-banner" role="alert">{safeMutationError(firstError).message}</div>}
    {staleContext && <div className="error-banner" role="status">This review result is stale for the current note revision. Refresh before taking an approval or decision action.</div>}
    <div className="workspace-grid">
      <StateCard title={`Current persisted revision · ${note.revision}`}>
        <label>Reviewer label<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label>
        <textarea aria-label="Editable nursing note" value={content} onChange={(event) => { setContent(event.target.value); setDraftContent(event.target.value); }} />
        <div className="button-row"><button onClick={saveRevision} disabled={save.isPending || content === note.content}>{save.isPending ? "Saving …" : "Save successor revision"}</button><button className="secondary-button" onClick={fullVerify} disabled={verify.isPending || save.isPending}>{verify.isPending ? "Verifying …" : "Run full verification"}</button></div>
        <p className="muted">Unsaved edits are not verified. Saving creates an immutable successor and invalidates prior findings for approval.</p>
      </StateCard>
      <StateCard title="Approval eligibility" tone={approvalEligible ? "neutral" : "warning"}>
        <div className="eligibility">{approvalEligible ? "Ready for approval" : "Not ready for approval"}</div>
        <p>{currentVerification ? (currentVerification.status === "VALID" ? "The note passed the current verification checks." : "The note still needs attention.") : "A complete verification is required before approval."}</p>
        {verify.isPending && <p className="muted">Verification is in progress; approval is disabled.</p>}
        {currentVerification?.failureMessage && <p className="muted">{userFacingFailureMessage(currentVerification.failureCode, currentVerification.failureMessage)}</p>}
        <div className="button-row"><button onClick={approveNote} disabled={!approvalEligible || approve.isPending}>{approve.isPending ? "Approving …" : "Approve"}</button><button className="danger-button" onClick={rejectNote} disabled={reject.isPending || reason.trim().length < 3}>Reject</button></div>
        <label>Rejection or suggestion rationale<input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Required for rejection/dispute" /></label>
      </StateCard>
      <StateCard title="Finding decisions">
        <div className="finding-list">{context?.findings.length ? context.findings.map((finding) => <div className="finding" key={finding.reviewFindingId}><span>{finding.reviewFindingId}</span><strong>{finding.state}</strong><p>{finding.explanation}</p><div className="button-row"><button className="secondary-button" onClick={() => recordDecision(finding.reviewFindingId, "ACKNOWLEDGED")}>Acknowledge</button><button className="secondary-button" onClick={() => recordDecision(finding.reviewFindingId, "DISPUTED")} disabled={reason.trim().length < 3}>Dispute</button></div></div>) : <p className="muted">No findings loaded for this revision.</p>}</div>
      </StateCard>
      <StateCard title="Suggested corrections">
        <div className="finding-list">{context?.suggestions.length ? context.suggestions.map((suggestion) => <div className="finding" key={suggestion.suggestionId}><span>{suggestion.suggestionId}</span><strong>{suggestion.supportStatus}</strong><p>Replace the backend-provided span with: {suggestion.replacement}</p><div className="button-row"><button onClick={() => suggestionDecision(suggestion.findingId, suggestion.suggestionId, "SUGGESTION_ACCEPTED")} disabled={suggestion.supportStatus !== "USABLE" || decide.isPending}>Accept explicitly</button><button className="secondary-button" onClick={() => suggestionDecision(suggestion.findingId, suggestion.suggestionId, "SUGGESTION_REJECTED")} disabled={suggestion.supportStatus !== "USABLE" || decide.isPending || reason.trim().length < 3}>Reject with rationale</button></div></div>) : <p className="muted">No backend-supported suggestions are available for this revision.</p>}</div>
      </StateCard>
      <StateCard title="Persisted audit history">
        <div className="finding-list">{audit.data?.events.length ? audit.data.events.map((event) => <div className="finding" key={event.eventId}><span>#{event.sequence} · {event.occurredAt}</span><strong>{event.eventType}</strong><p>{event.actorLabel} · revision {event.noteRevision}{event.rationale ? ` · ${event.rationale}` : ""}</p></div>) : <p className="muted">No audit events loaded yet.</p>}</div>
      </StateCard>
    </div>
  </>;
}

function notifyFailure(notify: ReturnType<typeof useToast>["notify"], title: string, error: unknown, unchanged: string) {
  const detail = safeMutationError(error);
  notify({ tone: "error", title, message: `${detail.message} ${unchanged}` });
}
