import { useEffect, useRef, useState } from "react";
import { safeMutationError, useApprove, useAudit, useFindingDecision, useFullVerification, useReject, useReview, useSaveRevision } from "../../api/hooks";
import { userFacingFailureMessage } from "../../api/errors";
import { StateCard } from "../../components/shared/StateCard";
import { useToast } from "../../components/shared/Toaster";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { useWorkspace } from "../../state/workspace";
import type { Finding } from "../../api/types";
import { projectSourceSpan } from "../verification/spans";
import { isFindingUnresolved } from "./findings";

export function ReviewWorkspace() {
  const { note: noteMaybe, draftContent, demo, setDraftContent, applyNoteRevision } = useWorkspace();
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
  const [selectedFindingId, setSelectedFindingId] = useState<string>();
  const latestRevisionRef = useRef(noteMaybe?.revision);
  latestRevisionRef.current = noteMaybe?.revision;

  useEffect(() => {
    setContent(draftContent ?? review.data?.candidateNote ?? noteMaybe?.content ?? "");
  }, [draftContent, review.data?.candidateNote, noteMaybe?.content]);

  if (!note) return <><WorkspaceHeader eyebrow="02 · HUMAN REVIEW" title="Resolve findings and approve safely" description="Edits create successor revisions. Approval remains controlled by the backend's latest complete-note verification." /><div className="empty-state">Create or import a note in Documentation first.</div></>;

  const context = review.data;
  const currentVerification = context?.fullVerification?.noteRevision === note.revision ? context.fullVerification : undefined;
  const hasUnsavedChanges = content !== note.content;
  const staleContext = Boolean(context && context.latestRevision > note.revision);
  const unresolvedFindings = context?.findings.some((finding) => isFindingUnresolved(finding, context.decisions)) ?? false;
  const approvalEligible = Boolean(context?.approvalEligible && currentVerification?.status === "VALID" && !hasUnsavedChanges && !unresolvedFindings && !review.error && !verify.isPending && !save.isPending);
  const firstError = review.error ?? save.error ?? verify.error ?? decide.error ?? approve.error ?? reject.error;
  const selectedFinding = context?.findings.find((finding) => finding.reviewFindingId === selectedFindingId) ?? context?.findings[0];
  const nextStep = hasUnsavedChanges
    ? { title: "Save your changes first", detail: "The edited text is not yet a saved note revision. Save it before verification or approval." }
    : !currentVerification
      ? { title: "Run full verification", detail: "Check this saved note against the original transcript before making a decision." }
      : currentVerification.status !== "VALID"
        ? { title: "Verification did not complete", detail: "Retry full verification. Approval is blocked until every verification check finishes successfully." }
        : unresolvedFindings
          ? { title: "Review the findings", detail: "Select each finding, compare its evidence with the note, then correct the note or record the appropriate review decision." }
          : approvalEligible
            ? { title: "Make the human decision", detail: "The exact saved revision is eligible. Approve it if it is accurate, or reject it with a rationale." }
            : { title: "Complete Human Review", detail: "Review the verification result and any required decisions before approval." };
  const demoStep = context?.noteStatus === "APPROVED"
    ? "COMPLETE"
    : context?.approvalEligible && currentVerification?.status === "VALID"
      ? "APPROVE"
      : note.content === demo?.correctedNote
        ? "REVERIFY"
        : "CORRECT";

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
    if (hasUnsavedChanges) {
      notify({ tone: "error", title: "Save the note before verification", message: "Full verification only runs against the exact saved note revision. Save your edits as a successor revision first." });
      return;
    }
    const verificationRevision = note.revision;
    try {
      const result = await verify.mutateAsync({ noteId: note.noteId, expectedRevision: note.revision, reviewerLabel: reviewer });
      if (latestRevisionRef.current !== verificationRevision) return;
      void review.refetch();
      if (result.status === "VALID") {
        notify({ tone: "info", title: "Verification run recorded", message: "Inspect the current findings and approval eligibility before approval." });
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
    if (!currentVerification || hasUnsavedChanges || !approvalEligible) return;
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
    <WorkspaceHeader eyebrow="02 · HUMAN REVIEW" title="Resolve findings and approve safely" description="Resolve the findings identified in Documentation & Verification. Edits create successor revisions and preserve the linked source, note, and evidence." />
    <section className="review-next-step" aria-live="polite" aria-label="What to do next"><span className="eyebrow">WHAT TO DO NEXT</span><h3>{nextStep.title}</h3><p>{nextStep.detail}</p></section>
    {demo && <section className="guided-demo" aria-label="Guided demo review progress"><span className="eyebrow">GUIDED DEMO · {demoStep === "COMPLETE" ? "COMPLETE" : `STEP ${demoStep}`}</span><h3>{demoStep === "COMPLETE" ? "Synthetic note approved" : demo.steps.find((step) => step.id === demoStep)?.title}</h3><p>{demoStep === "COMPLETE" ? "The audit history below records the explicit human approval for the corrected revision." : demo.steps.find((step) => step.id === demoStep)?.instruction}</p>{demoStep === "CORRECT" && <div className="button-row"><button className="secondary-button" onClick={() => { setContent(demo.correctedNote); setDraftContent(demo.correctedNote); }}>Apply evidence-supported demo correction</button></div>}</section>}
    {firstError && <div className="error-banner" role="alert">{safeMutationError(firstError).message}</div>}
    {staleContext && <div className="error-banner" role="status">This review result is stale for the current note revision. Refresh before taking an approval or decision action.</div>}
    <div className="workspace-grid">
      <StateCard title={`Current persisted revision · ${note.revision}`}>
        <p className="review-help">This is the note version currently being reviewed. The transcript remains the authoritative source.</p>
        <label><strong>Reviewer label</strong><input aria-describedby="reviewer-label-help" value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label><span id="reviewer-label-help" className="field-description">The name recorded in the audit history for your edits and decisions.</span>
        <label><strong>Candidate nursing note</strong><textarea aria-label="Editable nursing note" value={content} onChange={(event) => { setContent(event.target.value); setDraftContent(event.target.value); }} /></label>
        <p className="review-help">Edit this note only when a finding needs correction. The original version is preserved when you save.</p>
        <div className="button-row"><button onClick={saveRevision} disabled={save.isPending || !hasUnsavedChanges}>{save.isPending ? "Saving …" : "Save successor revision"}</button><button className="secondary-button" onClick={fullVerify} disabled={verify.isPending || save.isPending || hasUnsavedChanges} aria-describedby={hasUnsavedChanges ? "verification-save-required" : undefined}>{verify.isPending ? "Verifying …" : "Run full verification"}</button></div>
        <p className="review-help">Save successor revision creates a new version after an edit. Run full verification checks the currently saved version against the transcript.</p>
        <p id="verification-save-required" className="muted">{hasUnsavedChanges ? "Save the edited note as a new revision before running full verification." : "After saving an edit, run verification again before approval."}</p>
      </StateCard>
      <StateCard title="Approval eligibility" tone={approvalEligible ? "neutral" : "warning"}>
        <div className="eligibility">{approvalEligible ? "Human approval required" : "Approval blocked"}</div>
        <p>{currentVerification ? (currentVerification.status !== "VALID" ? "The verification run did not complete successfully. Retry it before approval." : approvalEligible ? "No unresolved issues are recorded. A human must still decide whether to approve this note." : "Review required. Unresolved issues must be resolved or adjudicated before approval.") : "A complete verification is required before approval."}</p>
        {currentVerification?.status !== "VALID" && <p className="review-help">Approval is blocked because the verification process did not complete successfully; an empty findings list is not a successful verification.</p>}
        {hasUnsavedChanges && <p role="status" className="muted">Unsaved changes are present. Save them as a new revision and run verification before approval.</p>}
        {verify.isPending && <p className="muted">Verification is in progress; approval is disabled.</p>}
        {currentVerification?.failureMessage && <p className="muted">{userFacingFailureMessage(currentVerification.failureCode, currentVerification.failureMessage)}</p>}
        <div className="button-row"><button onClick={approveNote} disabled={!approvalEligible || approve.isPending}>{approve.isPending ? "Approving …" : "Approve"}</button><button className="danger-button" onClick={rejectNote} disabled={reject.isPending || reason.trim().length < 3}>Reject</button></div>
        <p className="review-help">Approve records human acceptance of this exact verified revision. Reject records that this revision should not be used; rejection remains available when verification fails.</p>
        <label>Reviewer rationale<input aria-describedby="rationale-help" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain a rejection, dispute, or rejected suggestion" /></label><span id="rationale-help" className="field-description">Required for Reject, Dispute, and Reject suggestion actions.</span>
      </StateCard>
      <StateCard title="Evidence for the selected finding" description="Select a finding below to see the affected note text and matching transcript evidence.">
        <ReviewEvidence finding={selectedFinding} transcript={context?.transcriptText ?? ""} candidateNote={context?.candidateNote ?? note.content} />
      </StateCard>
      <StateCard title="Finding decisions">
        <div className="review-help" role="note"><p><b>Acknowledge</b> accepts the finding. <b>Dispute</b> flags it as incorrect; add a rationale. Neither action approves the note.</p></div>
        <div className="finding-list">{context?.findings.length ? context.findings.map((finding) => { const decision = [...(context.decisions ?? [])].reverse().find((item) => item.findingId === finding.reviewFindingId); const decisionState = decision?.kind === "ACKNOWLEDGED" ? "ACKNOWLEDGED" : decision?.kind === "DISPUTED" ? "DISPUTED" : finding.state; return <div className={`finding ${selectedFinding?.reviewFindingId === finding.reviewFindingId ? "selected" : ""}`} key={finding.reviewFindingId}><button className="finding-select" onClick={() => setSelectedFindingId(finding.reviewFindingId)} aria-pressed={selectedFinding?.reviewFindingId === finding.reviewFindingId}><span>{finding.reviewFindingId}</span><strong>{decisionState} · {finding.severity}</strong><p>{finding.explanation}</p></button><div className="button-row"><button className="secondary-button" onClick={() => recordDecision(finding.reviewFindingId, "ACKNOWLEDGED")} disabled={Boolean(decision)}>Acknowledge</button><button className="secondary-button" onClick={() => recordDecision(finding.reviewFindingId, "DISPUTED")} disabled={Boolean(decision) || reason.trim().length < 3}>Dispute</button></div></div>}) : <div className="review-help"><strong>No findings for this revision.</strong><p>After a successful verification, this means the verifier recorded no issues. If verification failed, retry it before treating the note as clear.</p></div>}</div>
      </StateCard>
      <StateCard title="Suggested corrections">
        <div className="finding-list">{context?.suggestions.length ? context.suggestions.map((suggestion) => <div className="finding" key={suggestion.suggestionId}><span>{suggestion.suggestionId}</span><strong>{suggestion.supportStatus}</strong><p>Replace the backend-provided span with: {suggestion.replacement}</p><div className="button-row"><button onClick={() => suggestionDecision(suggestion.findingId, suggestion.suggestionId, "SUGGESTION_ACCEPTED")} disabled={suggestion.supportStatus !== "USABLE" || decide.isPending}>Accept explicitly</button><button className="secondary-button" onClick={() => suggestionDecision(suggestion.findingId, suggestion.suggestionId, "SUGGESTION_REJECTED")} disabled={suggestion.supportStatus !== "USABLE" || decide.isPending || reason.trim().length < 3}>Reject with rationale</button></div></div>) : <div className="review-help"><strong>No suggested corrections are available.</strong><p>Suggestions appear only when the backend has source-supported replacement wording. You can always correct the note manually above.</p></div>}</div>
      </StateCard>
      <StateCard title="Persisted audit history">
        <p className="review-help">This append-only history records saved revisions, verification runs, decisions, and final approval or rejection. It lets you see what happened and which revision each action affected.</p>
        <div className="finding-list">{audit.data?.events.length ? audit.data.events.map((event) => <div className="finding" key={event.eventId}><span>#{event.sequence} · {event.occurredAt}</span><strong>{event.eventType}</strong><p>{event.actorLabel} · revision {event.noteRevision}{event.rationale ? ` · ${event.rationale}` : ""}</p></div>) : <p className="muted">No audit events have been recorded for this note yet.</p>}</div>
      </StateCard>
    </div>
  </>;
}

function ReviewEvidence({ finding, transcript, candidateNote }: { finding?: Finding; transcript: string; candidateNote: string }) {
  if (!finding) return <p className="muted">No finding is available for this revision.</p>;
  const claimText = finding.claimSpan ? projectNoteSpan(candidateNote, finding.claimSpan.startCodePoint, finding.claimSpan.endCodePointExclusive) : undefined;
  const excerpts = finding.evidence.availability === "AVAILABLE" ? finding.evidence.spans
    .filter((span) => span.sourceId === finding.sourceId && span.sourceVersion === finding.sourceVersion)
    .map((span) => projectSourceSpan(transcript, span))
    .filter((excerpt): excerpt is string => Boolean(excerpt)) : [];
  return <div className="review-evidence"><div className="finding-summary"><span className="status-label">{finding.upstreamStatus ?? "REVIEW FINDING"}</span><span className="status-label">{finding.severity}</span><span className="status-label">{finding.origin}</span></div><p>{finding.explanation}</p><h4>Candidate note reference</h4><p className="evidence-note">{claimText ?? "No valid candidate-note span is available for this finding."}</p><h4>Source evidence</h4>{excerpts.length ? excerpts.map((excerpt, index) => <p className="evidence-note" key={`${finding.reviewFindingId}-${index}`}>{excerpt}</p>) : <p className="muted">Evidence is {finding.evidence.availability.toLowerCase()}; no source excerpt is shown.</p>}</div>;
}

function projectNoteSpan(text: string, start: number, end: number): string | undefined {
  const codePoints = Array.from(text);
  if (start < 0 || end <= start || end > codePoints.length) return undefined;
  return codePoints.slice(start, end).join("");
}

function notifyFailure(notify: ReturnType<typeof useToast>["notify"], title: string, error: unknown, unchanged: string) {
  const detail = safeMutationError(error);
  notify({ tone: "error", title, message: `${detail.message} ${unchanged}` });
}
