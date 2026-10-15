import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { safeMutationError, useCreateSource, useFullVerification, useGenerateNote, useHealth, useImportNote, useReview, useSavedExamples, useSource } from "../../api/hooks";
import { userFacingFailureMessage } from "../../api/errors";
import type { NursingFact, NoteResponse, SourceDocument } from "../../api/types";
import { StateCard } from "../../components/shared/StateCard";
import { LoadingIndicator } from "../../components/shared/LoadingIndicator";
import { useToast } from "../../components/shared/Toaster";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { VerificationResults } from "../../features/verification/VerificationPage";
import { useWorkspace } from "../../state/workspace";
import { isDuplicateGeneratedNote, isExternalNoteValid, isTranscriptValid } from "./validation";

export function DocumentationVerificationPage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const { setSource, source, note, setNote, applyNoteRevision, setDraftContent } = useWorkspace();
  const examples = useSavedExamples();
  const createSource = useCreateSource();
  const generate = useGenerateNote();
  const importNote = useImportNote();
  const fullVerification = useFullVerification();
  const health = useHealth();
  const review = useReview(note?.noteId, note?.revision);
  const [transcript, setTranscript] = useState("");
  const [residentId, setResidentId] = useState("synthetic-resident-demo");
  const [selectedExample, setSelectedExample] = useState("");
  const [workspaceMode, setWorkspaceMode] = useState<"documentation" | "verification">("documentation");
  const [noteMethod, setNoteMethod] = useState<"generate" | "existing">("generate");
  const [existingNote, setExistingNote] = useState("");
  const [isEditingSource, setIsEditingSource] = useState(false);
  const [generatedFacts, setGeneratedFacts] = useState<NursingFact[]>();
  const [generatedResidentId, setGeneratedResidentId] = useState<string>();
  const example = examples.data?.find((item) => item.exampleId === selectedExample);
  const sourceQuery = useSource(example?.sourceId, example?.sourceVersion);
  const error = examples.error ?? sourceQuery.error ?? createSource.error ?? generate.error ?? importNote.error ?? fullVerification.error;

  function clearCandidate() {
    setNote(undefined);
    setDraftContent(undefined);
    setGeneratedFacts(undefined);
    setGeneratedResidentId(undefined);
    setExistingNote("");
  }

  async function loadExample() {
    if (!example) return;
    try {
      const result = await sourceQuery.refetch();
      if (!result.data) throw result.error ?? new Error("The saved example did not return a source document.");
      setSource(result.data);
      setTranscript(result.data.transcript_text);
      setResidentId(result.data.resident_test_id);
      setIsEditingSource(false);
      clearCandidate();
      notify({ tone: "success", title: "Example loaded", message: "Review the transcript, then generate the nursing note when it is ready." });
    } catch (actionError) {
      notifyFailure(notify, "Saved example could not be loaded", actionError, "The current transcript and candidate note were not changed.");
    }
  }

  async function sourceForVerification(): Promise<SourceDocument | undefined> {
    if (source && !isEditingSource) return source;
    if (!isTranscriptValid(transcript)) return undefined;
    const result = await createSource.mutateAsync({ resident_test_id: residentId.trim(), language: "de-DE", transcript_text: transcript });
    setSource(result);
    setIsEditingSource(false);
    clearCandidate();
    return result;
  }

  function handleManualTranscriptChange(value: string) {
    setTranscript(value);
    setSelectedExample("");
  }

  async function verify(noteToVerify: NoteResponse): Promise<void> {
    const result = await fullVerification.mutateAsync({ noteId: noteToVerify.noteId, expectedRevision: noteToVerify.revision, reviewerLabel: "synthetic-reviewer" });
    if (result.status === "VALID") {
      notify({ tone: "info", title: "Verification run recorded", message: "Inspect the current findings and approval eligibility before Human Review." });
    } else {
      notify({ tone: "error", title: "The note needs attention", message: `${userFacingFailureMessage(result.failureCode, result.failureMessage)} The note remains read-only until Human Review.` });
    }
  }

  async function generateAndVerify() {
    let activeSource: SourceDocument | undefined;
    try {
      activeSource = await sourceForVerification();
    } catch (actionError) {
      notifyFailure(notify, "Transcript was not saved", actionError, "No candidate note was created.");
      return;
    }
    if (!activeSource) return;

    const reusableNote = note;
    if (reusableNote && isDuplicateGeneratedNote(reusableNote, activeSource, reusableNote.content, generatedFacts, generatedResidentId)) {
      const currentVerification = review.data?.fullVerification;
      if (currentVerification?.noteId === reusableNote.noteId && currentVerification.noteRevision === reusableNote.revision) {
        notify({ tone: "info", title: "Existing note reused", message: "Nothing changed, so the existing note and its check results were reused." });
        return;
      }
      try {
        await verify(reusableNote);
      } catch (actionError) {
        notifyFailure(notify, "Verification could not run", actionError, "The existing candidate was retained and remains in its prior verification state.");
      }
      return;
    }

    let generated: NoteResponse;
    try {
      generated = await generate.mutateAsync({ sourceId: activeSource.source_id, sourceVersion: activeSource.source_version, requestedBy: "synthetic-reviewer" });
      applyNoteRevision(generated);
      setDraftContent(generated.content);
      setGeneratedFacts(generated.facts);
      setGeneratedResidentId(activeSource.resident_test_id);
      notify({ tone: "success", title: "Draft note created", message: "The nursing note was created. It is now being checked against the transcript." });
    } catch (actionError) {
      notifyFailure(notify, "Note generation failed", actionError, "The saved source was retained; no candidate note was created.");
      return;
    }

    try {
      await verify(generated);
    } catch (actionError) {
      notifyFailure(notify, "Verification could not run", actionError, "The generated candidate was retained as read-only, but it remains in its prior verification state and is not approval-eligible.");
    }
  }

  async function verifyExistingNote() {
    let activeSource: SourceDocument | undefined;
    try {
      activeSource = await sourceForVerification();
    } catch (actionError) {
      notifyFailure(notify, "Transcript was not saved", actionError, "No existing note was imported.");
      return;
    }
    if (!activeSource || !isExternalNoteValid(existingNote)) return;

    let imported: NoteResponse;
    try {
      imported = await importNote.mutateAsync({ sourceId: activeSource.source_id, sourceVersion: activeSource.source_version, content: existingNote, externalOrigin: { system: "synthetic-external-demo", externalNoteId: `external-${Date.now()}` }, requestedBy: "synthetic-reviewer", facts: [] });
      applyNoteRevision(imported);
      setDraftContent(imported.content);
      setGeneratedFacts(undefined);
      setGeneratedResidentId(undefined);
      notify({ tone: "success", title: "Existing note imported", message: "The supplied note is now being checked against its locked source transcript." });
    } catch (actionError) {
      notifyFailure(notify, "Existing note could not be imported", actionError, "The source was retained and no note was verified.");
      return;
    }

    try {
      await verify(imported);
    } catch (actionError) {
      notifyFailure(notify, "Verification could not run", actionError, "The imported note was retained for Human Review but is not approval-eligible.");
    }
  }

  const processing = createSource.isPending || generate.isPending || importNote.isPending || fullVerification.isPending;
  const providerLabel = (provider: "LIVE_AI" | "OFFLINE_DEMO" | "UNAVAILABLE" | undefined) => provider === "LIVE_AI" ? "Live AI provider" : provider === "OFFLINE_DEMO" ? "Offline demo" : "Status unavailable";
  const generationReadiness = health.data?.generation;
  return <>
    <WorkspaceHeader eyebrow="01 · DOCUMENTATION & VERIFICATION" title="Create or verify a source-bound nursing note" description="Start with a synthetic German transcript, then either generate a new note or verify an existing AI-generated note before Human Review." />
    {error && <div className="error-banner" role="alert">{safeMutationError(error).message}</div>}
    <section className="documentation-verification-section" aria-label="Documentation and verification workflow">
      <div className="workspace-mode-switch" role="tablist" aria-label="Documentation and verification mode">
        <button type="button" role="tab" aria-selected={workspaceMode === "documentation"} aria-controls="documentation-mode" className={workspaceMode === "documentation" ? "selected" : ""} onClick={() => setWorkspaceMode("documentation")}>Documentation</button>
        <button type="button" role="tab" aria-selected={workspaceMode === "verification"} aria-controls="verification-mode" className={workspaceMode === "verification" ? "selected" : ""} onClick={() => setWorkspaceMode("verification")}>Verification</button>
      </div>
      <p className="workspace-mode-description">Switch between the documentation workspace and the verification workspace. Only the selected workspace is shown.</p>
      {workspaceMode === "documentation" && <div id="documentation-mode"><StateCard title="Documentation" description="Enter and correct the transcript, then generate or import the source-bound nursing note.">
        <div className="provider-status" role="status" aria-label="Provider status"><span>Generation: <strong>{providerLabel(health.data?.generationProvider)}</strong></span><span>LLM: <strong>{generationReadiness?.available ? `Loaded${generationReadiness.model ? ` (${generationReadiness.model})` : ""}` : "Unavailable"}</strong></span><span>Verification: <strong>{providerLabel(health.data?.verificationProvider)}</strong></span></div>
        {!generationReadiness?.available && <p className="field-description" role="status">Live note generation is unavailable because the LLM configuration is not loaded.</p>}
        <div className="workflow-step">
          <h4>1. Enter and check the transcript</h4>
          <p className="workflow-step-description">Enter a synthetic transcript or load an example. Correct speech-to-text mistakes here before generating the note.</p>
          <label>German transcript (manual entry)<textarea aria-label="German transcript" readOnly={Boolean(source) && !isEditingSource} required aria-invalid={!isTranscriptValid(transcript)} value={transcript} onChange={(event) => handleManualTranscriptChange(event.target.value)} placeholder="Type or paste the German transcript here …" /></label><span className="field-description">Type or paste the synthetic German transcript you want to document.</span>
          <label>Example transcript (optional)<select aria-label="Example transcript" disabled={Boolean(source) && !isEditingSource} value={selectedExample} onChange={(event) => setSelectedExample(event.target.value)}><option value="">Choose an example transcript …</option>{examples.data?.map((item) => <option key={item.exampleId} value={item.exampleId}>{item.title}</option>)}</select></label><span className="field-description">Choose an example to preview its content first, then use it to replace the manual transcript.</span>
          {example && <div className="example-preview" aria-label="Selected example preview" aria-live="polite"><div className="example-preview-header"><span>Example preview</span><strong>{example.title}</strong></div>{sourceQuery.isFetching && <p className="loading-message"><LoadingIndicator label="Loading example transcript …" /></p>}{sourceQuery.data && <p className="example-preview-text">{sourceQuery.data.transcript_text}</p>}{sourceQuery.error && <p className="muted">This example preview could not be loaded. You can continue with manual entry.</p>}</div>}
          {example && sourceQuery.data && <button className="secondary-button" onClick={loadExample} disabled={sourceQuery.isFetching || Boolean(source) && !isEditingSource}>{sourceQuery.isFetching ? <LoadingIndicator label="Loading example …" /> : "Use selected example"}</button>}
          <label>Synthetic resident identifier<input aria-label="Synthetic resident identifier" readOnly={Boolean(source) && !isEditingSource} value={residentId} onChange={(event) => setResidentId(event.target.value)} /></label><span className="field-description">This identifier links the transcript and generated nursing note to the synthetic resident test case.</span>
          <div className="button-row">{source && !isEditingSource && <button className="secondary-button" onClick={() => setIsEditingSource(true)}>Edit source</button>}{source && isEditingSource && <button className="secondary-button" onClick={() => { setTranscript(source.transcript_text); setResidentId(source.resident_test_id); setIsEditingSource(false); }}>Cancel edit</button>}</div>
          {source && <div className="identity-pill">Locked source snapshot · {source.source_id} · v{source.source_version} · {source.language}</div>}
        </div>
        <div className="workflow-step">
          <h4>2. Choose a verification path</h4>
          <p className="workflow-step-description">Both paths preserve the same transcript, note, findings, and evidence for Human Review. This workspace identifies and explains issues; it does not edit or approve notes.</p>
          <div className="segmented" role="tablist" aria-label="Verification mode"><button type="button" role="tab" aria-selected={noteMethod === "generate"} className={noteMethod === "generate" ? "selected" : ""} onClick={() => setNoteMethod("generate")}>Generate &amp; Verify</button><button type="button" role="tab" aria-selected={noteMethod === "existing"} className={noteMethod === "existing" ? "selected" : ""} onClick={() => setNoteMethod("existing")}>Verify Existing Note</button></div>
          {noteMethod === "generate" ? <><h4>Generate &amp; Verify</h4><p className="muted">The transcript is saved automatically if needed. The AI generates a structured draft, then the engine verifies it against this exact source version.</p><button aria-busy={processing} onClick={generateAndVerify} disabled={processing || !isTranscriptValid(transcript)}>{processing ? <LoadingIndicator label={createSource.isPending ? "Saving transcript …" : generate.isPending ? "Generating nursing note …" : "Checking nursing note …"} /> : "Generate note & verify"}</button></> : <><h4>Verify Existing Note</h4><p className="muted">Paste an existing synthetic AI-generated note. The engine compares this supplied note to the transcript without generating a replacement.</p><label>Existing AI-generated note<textarea aria-label="Existing AI-generated note" value={existingNote} onChange={(event) => setExistingNote(event.target.value)} placeholder="Fügen Sie die vorhandene KI-generierte Pflegenotiz ein …" /></label><button aria-busy={processing} onClick={verifyExistingNote} disabled={processing || !isTranscriptValid(transcript) || !isExternalNoteValid(existingNote)}>{processing ? <LoadingIndicator label={createSource.isPending ? "Saving transcript …" : importNote.isPending ? "Importing existing note …" : "Checking nursing note …"} /> : "Verify Note"}</button></>}
          {note && <><div className="identity-pill">Candidate note · {note.noteId} · revision {note.revision} · {note.origin}</div><FactList facts={note.facts} /><button className="secondary-button" onClick={() => navigate("/review")}>Continue to Human Review</button></>}
        </div>
      </StateCard></div>}
      {workspaceMode === "verification" && <div id="verification-mode" className="verification-results" role="tabpanel" aria-label="Verification">
        <div className="verification-results-header"><span className="eyebrow">03 · RESULTS</span><h3>Inspect verification results</h3><p>Select a finding to see the affected note text, explanation, severity, and source-bound evidence. Corrections and approval remain in Human Review.</p></div>
        {note ? <VerificationResults note={note} source={source} context={review.data} isLoading={review.isLoading || review.isFetching || fullVerification.isPending} loadError={review.error} onRetry={() => { void review.refetch(); }} /> : <div className="empty-state">No candidate note is available yet. Return to Documentation to create or import a note, then switch back here to inspect its verification results.</div>}
      </div>}
    </section>
  </>;
}

function notifyFailure(notify: ReturnType<typeof useToast>["notify"], title: string, error: unknown, unchanged: string) {
  const detail = safeMutationError(error);
  notify({ tone: "error", title, message: `${detail.message} ${unchanged}` });
}

function FactList({ facts }: { facts: NursingFact[] }) {
  const groups = ["OBSERVATION", "SYMPTOM", "MEASUREMENT", "ACTION"] as const;
  return <div className="facts"><h4>Structured facts returned by backend</h4>{groups.map((group) => <div key={group}><strong>{group}</strong>{facts.filter((fact) => fact.type === group).map((fact) => <p key={fact.factId}>{fact.statement}{fact.numericValue ? ` · ${fact.numericValue} ${fact.unit ?? ""}` : ""}</p>)}{facts.every((fact) => fact.type !== group) && <p className="muted">Absent</p>}</div>)}</div>;
}
