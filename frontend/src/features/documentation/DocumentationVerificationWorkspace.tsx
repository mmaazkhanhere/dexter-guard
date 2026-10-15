import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { safeMutationError, useCreateSource, useFullVerification, useGenerateNote, useHealth, useImportNote, useReview, useSavedExamples, useSource } from "../../api/hooks";
import { userFacingFailureMessage } from "../../api/errors";
import type { Health, NoteResponse, SourceDocument } from "../../api/types";
import { LoadingIndicator } from "../../components/shared/LoadingIndicator";
import { StateCard } from "../../components/shared/StateCard";
import { useToast } from "../../components/shared/Toaster";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { VerificationResults } from "../verification/VerificationPage";
import { useWorkspace } from "../../state/workspace";
import {
  existingNoteValidationMessage,
  isExternalNoteValid,
  isResidentIdValid,
  isTranscriptValid,
  residentIdValidationMessage,
  transcriptValidationMessage,
} from "./validation";

type Mode = "generate" | "existing";

export function verificationModeCopy(provider?: Health["verificationProvider"]) {
  if (provider === "LIVE_AI") return {
    label: "Live LLM verification",
    detail: "A configured live LLM processes the claim evidence for this verification run.",
  };
  if (provider === "OFFLINE_DEMO") return {
    label: "Offline replay",
    detail: "The local demo verifier is running; no live LLM request or setup is required.",
  };
  return {
    label: "Verification mode loading",
    detail: "Checking whether verification uses the local demo verifier or a configured live LLM.",
  };
}

export function DocumentationVerificationWorkspace() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const { source, note, transcript: savedTranscript, residentId: savedResidentId, demo, setSource, setNote, setTranscript: saveTranscript, setResidentId: saveResidentId, applyNoteRevision, setDraftContent } = useWorkspace();
  const createSource = useCreateSource();
  const generate = useGenerateNote();
  const importNote = useImportNote();
  const fullVerification = useFullVerification();
  const health = useHealth();
  const review = useReview(note?.noteId, note?.revision);
  const examples = useSavedExamples();
  const [mode, setMode] = useState<Mode>("generate");
  const [transcript, setTranscript] = useState(savedTranscript ?? "");
  const [residentId, setResidentId] = useState(savedResidentId ?? "synthetic-resident-demo");
  const [existingNote, setExistingNote] = useState("");
  const [selectedExample, setSelectedExample] = useState("");
  const [editingSource, setEditingSource] = useState(false);
  const [generatedIdentity, setGeneratedIdentity] = useState<{ sourceId: string; sourceVersion: number }>();
  const selectedScenario = examples.data?.find((example) => example.exampleId === selectedExample);
  const scenarioSource = useSource(selectedScenario?.sourceId, selectedScenario?.sourceVersion);
  const error = createSource.error ?? generate.error ?? importNote.error ?? fullVerification.error;
  const isWorking = createSource.isPending || generate.isPending || importNote.isPending || fullVerification.isPending;
  const activeResult = note && (demo || (mode === "generate" ? note.origin === "GENERATED" : note.origin === "IMPORTED")) ? note : undefined;
  const demoVerification = review.data?.fullVerification?.noteRevision === note?.revision ? review.data?.fullVerification : undefined;
  const demoStep = note?.content === demo?.correctedNote
    ? (demoVerification?.status === "VALID" ? "APPROVE" : "REVERIFY")
    : (!demoVerification ? "VERIFY" : "CORRECT");
  const verificationMode = verificationModeCopy(health.data?.verificationProvider);

  useEffect(() => {
    if (!transcript && savedTranscript) setTranscript(savedTranscript);
    if (residentId === "synthetic-resident-demo" && savedResidentId) setResidentId(savedResidentId);
  }, [residentId, savedResidentId, savedTranscript, transcript]);

  useEffect(() => {
    if (demo) setMode("existing");
  }, [demo]);

  function updateTranscript(value: string) {
    setTranscript(value);
    saveTranscript(value);
  }

  function updateResidentId(value: string) {
    setResidentId(value);
    saveResidentId(value);
  }

  async function ensureSource(): Promise<SourceDocument | undefined> {
    if (source && !editingSource) return source;
    if (!isTranscriptValid(transcript) || !isResidentIdValid(residentId.trim())) return undefined;
    const created = await createSource.mutateAsync({ resident_test_id: residentId.trim(), language: "de-DE", transcript_text: transcript });
    setSource(created);
    setEditingSource(false);
    return created;
  }

  async function loadScenario() {
    if (!selectedScenario) return;
    try {
      const result = await scenarioSource.refetch();
      if (!result.data) throw result.error ?? new Error("The selected scenario could not be loaded.");
      setSource(result.data);
      updateTranscript(result.data.transcript_text);
      updateResidentId(result.data.resident_test_id);
      setNote(undefined);
      setDraftContent(undefined);
      setGeneratedIdentity(undefined);
      setEditingSource(false);
      notify({ tone: "success", title: "Example scenario loaded", message: "The immutable synthetic transcript is ready to generate and verify." });
    } catch (failure) {
      notify({ tone: "error", title: "Example scenario could not be loaded", message: `${safeMutationError(failure).message} The current source was not changed.` });
    }
  }

  async function verify(candidate: NoteResponse) {
    const result = await fullVerification.mutateAsync({ noteId: candidate.noteId, expectedRevision: candidate.revision, reviewerLabel: "synthetic-reviewer" });
    if (result.status === "VALID") {
      notify({ tone: "info", title: "Verification run recorded", message: "Inspect the current findings and approval eligibility before Human Review." });
    } else {
      notify({ tone: "error", title: "Verification did not complete", message: `${userFacingFailureMessage(result.failureCode, result.failureMessage)} The note is not approval-eligible.` });
    }
  }

  async function generateAndVerify() {
    try {
      const activeSource = await ensureSource();
      if (!activeSource) return;
      if (note?.origin === "GENERATED" && generatedIdentity?.sourceId === activeSource.source_id && generatedIdentity.sourceVersion === activeSource.source_version) {
        await verify(note);
        return;
      }
      const generated = await generate.mutateAsync({ sourceId: activeSource.source_id, sourceVersion: activeSource.source_version, requestedBy: "synthetic-reviewer" });
      applyNoteRevision(generated);
      setDraftContent(generated.content);
      setGeneratedIdentity({ sourceId: activeSource.source_id, sourceVersion: activeSource.source_version });
      await verify(generated);
    } catch (failure) {
      const detail = safeMutationError(failure);
      notify({ tone: "error", title: "Generate & Verify could not finish", message: `${detail.message} No factual success or approval was recorded.` });
    }
  }

  async function verifyExistingNote() {
    try {
      const activeSource = await ensureSource();
      if (!activeSource || !isExternalNoteValid(existingNote)) return;
      const imported = await importNote.mutateAsync({ sourceId: activeSource.source_id, sourceVersion: activeSource.source_version, content: existingNote, externalOrigin: { system: "synthetic-external-demo", externalNoteId: `external-${Date.now()}` }, requestedBy: "synthetic-reviewer", facts: [] });
      applyNoteRevision(imported);
      setDraftContent(imported.content);
      await verify(imported);
    } catch (failure) {
      const detail = safeMutationError(failure);
      notify({ tone: "error", title: "Verify Note could not finish", message: `${detail.message} No factual success or approval was recorded.` });
    }
  }

  const busyLabel = createSource.isPending ? "Saving transcript …" : generate.isPending ? "Generating nursing note …" : importNote.isPending ? "Importing note …" : "Verifying note …";
  const sourceLocked = Boolean(source) && !editingSource;
  const panelId = mode === "generate" ? "generate-and-verify-panel" : "verify-existing-note-panel";

  return <>
    <WorkspaceHeader eyebrow="01 · DOCUMENTATION & VERIFICATION" title="Nursing note verification" description="Synthetic data only. Select one workflow, provide the original caregiver transcript, then inspect evidence-linked verification results." />
    {demo && <section className="guided-demo" aria-label="Guided demo progress"><span className="eyebrow">GUIDED DEMO · STEP {demoStep}</span><h3>{demo.steps.find((step) => step.id === demoStep)?.title}</h3><p>{demo.steps.find((step) => step.id === demoStep)?.instruction}</p><ol>{demo.steps.map((step) => <li className={step.id === demoStep ? "current" : ""} key={step.id}>{step.title}</li>)}</ol>{(demoStep === "VERIFY" || demoStep === "REVERIFY") && <div className="button-row"><button onClick={() => note && void verify(note)} disabled={isWorking}>{demoStep === "REVERIFY" ? "Re-verify corrected revision" : "Run guided verification"}</button></div>}{(demoStep === "CORRECT" || demoStep === "APPROVE") && <div className="button-row"><button className="secondary-button" onClick={() => navigate("/review")}>{demoStep === "APPROVE" ? "Continue to human approval" : "Inspect and correct findings"}</button></div>}</section>}
    <section className="verification-mode" role="status" aria-label="Verification mode"><strong>Verification mode: {verificationMode.label}</strong><p>{health.isError ? "Verification configuration could not be loaded. The result screen will still show whether each verification run completed." : verificationMode.detail}</p></section>
    {error && <div className="error-banner" role="alert">{safeMutationError(error).message}</div>}
    <section className="documentation-verification-section" aria-label="Documentation and verification workflow">
      <div className="segmented primary-mode-switch" role="tablist" aria-label="Nursing note workflow">
        <button role="tab" type="button" aria-selected={mode === "generate"} aria-controls="generate-and-verify-panel" className={mode === "generate" ? "selected" : ""} onClick={() => setMode("generate")}>Generate &amp; Verify</button>
        <button role="tab" type="button" aria-selected={mode === "existing"} aria-controls="verify-existing-note-panel" className={mode === "existing" ? "selected" : ""} onClick={() => setMode("existing")}>Verify Existing Note</button>
      </div>
      {mode === "generate" ? <ModePanel id={panelId} mode="generate" transcript={transcript} residentId={residentId} sourceLocked={sourceLocked} transcriptError={transcriptValidationMessage(transcript)} residentError={residentIdValidationMessage(residentId.trim())} onTranscript={updateTranscript} onResident={updateResidentId} onEditSource={() => setEditingSource(true)} onCancelEdit={() => { updateTranscript(source?.transcript_text ?? transcript); updateResidentId(source?.resident_test_id ?? residentId); setEditingSource(false); }} source={source} scenarios={examples.data?.map((example) => ({ id: example.exampleId, title: example.title }))} selectedScenario={selectedExample} onScenarioChange={setSelectedExample} onLoadScenario={loadScenario} scenarioLoading={scenarioSource.isFetching} action={<button onClick={generateAndVerify} disabled={isWorking || !isTranscriptValid(transcript) || !isResidentIdValid(residentId.trim())}>{isWorking ? <LoadingIndicator label={busyLabel} /> : "Generate note & verify"}</button>} /> : <ModePanel id={panelId} mode="existing" transcript={transcript} residentId={residentId} sourceLocked={sourceLocked} transcriptError={transcriptValidationMessage(transcript)} residentError={residentIdValidationMessage(residentId.trim())} noteError={existingNoteValidationMessage(existingNote)} onTranscript={updateTranscript} onResident={updateResidentId} onEditSource={() => setEditingSource(true)} onCancelEdit={() => { updateTranscript(source?.transcript_text ?? transcript); updateResidentId(source?.resident_test_id ?? residentId); setEditingSource(false); }} source={source} existingNote={existingNote} onExistingNote={setExistingNote} action={<button onClick={verifyExistingNote} disabled={isWorking || !isTranscriptValid(transcript) || !isResidentIdValid(residentId.trim()) || !isExternalNoteValid(existingNote)}>{isWorking ? <LoadingIndicator label={busyLabel} /> : "Verify Note"}</button>} />}
      {activeResult && <section className="verification-results" aria-label="Verification results">
        <div className="verification-results-header"><span className="eyebrow">VERIFICATION RESULTS</span><h3>Review the note against its evidence</h3><p>A completed run is not a factual pass. Select a finding to highlight the affected statement in the note and the supporting or contradicting source evidence.</p></div>
        <VerificationResults note={activeResult} source={source} context={review.data} isLoading={review.isLoading || review.isFetching || fullVerification.isPending} loadError={review.error} onRetry={() => { void review.refetch(); }} />
        <div className="button-row"><button className="secondary-button" onClick={() => navigate("/review")}>Continue to Human Review</button></div>
      </section>}
    </section>
  </>;
}

type ModePanelProps = {
  id: string; mode: Mode; transcript: string; residentId: string; sourceLocked: boolean; source?: SourceDocument; existingNote?: string;
  transcriptError?: string; residentError?: string; noteError?: string;
  scenarios?: Array<{ id: string; title: string }>; selectedScenario?: string; onScenarioChange?: (value: string) => void; onLoadScenario?: () => void; scenarioLoading?: boolean;
  onTranscript: (value: string) => void; onResident: (value: string) => void; onExistingNote?: (value: string) => void;
  onEditSource: () => void; onCancelEdit: () => void; action: ReactNode;
};

function ModePanel({ id, mode, transcript, residentId, sourceLocked, source, existingNote, transcriptError, residentError, noteError, scenarios, selectedScenario, onScenarioChange, onLoadScenario, scenarioLoading, onTranscript, onResident, onExistingNote, onEditSource, onCancelEdit, action }: ModePanelProps) {
  const generating = mode === "generate";
  return <div id={id} role="tabpanel">
    <StateCard title={generating ? "Generate & Verify" : "Verify Existing Note"} description={generating ? "Generate a professional nursing note, then automatically verify it against the original transcript." : "Verify an existing AI-generated nursing note without generating a replacement."}>
      {generating && <div className="example-scenarios"><label>Example scenario<select aria-label="Example scenario" disabled={sourceLocked} value={selectedScenario} onChange={(event) => onScenarioChange?.(event.target.value)}><option value="">Choose a synthetic scenario …</option>{scenarios?.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.title}</option>)}</select></label><button type="button" className="secondary-button" disabled={!selectedScenario || scenarioLoading || sourceLocked} onClick={onLoadScenario}>{scenarioLoading ? "Loading scenario …" : "Load example scenario"}</button></div>}
      <label>Original caregiver transcript<textarea aria-label="German transcript" readOnly={sourceLocked} aria-invalid={Boolean(transcriptError)} aria-describedby={transcriptError ? "transcript-error" : undefined} value={transcript} onChange={(event) => onTranscript(event.target.value)} placeholder="Original German caregiver transcript …" /></label>{transcriptError && <p id="transcript-error" className="field-error" role="alert">{transcriptError}</p>}
      <label>Synthetic resident identifier<input aria-label="Synthetic resident identifier" readOnly={sourceLocked} aria-invalid={Boolean(residentError)} aria-describedby={residentError ? "resident-id-error" : undefined} value={residentId} onChange={(event) => onResident(event.target.value)} /></label>{residentError && <p id="resident-id-error" className="field-error" role="alert">{residentError}</p>}
      {sourceLocked && <div className="button-row"><button type="button" className="secondary-button" onClick={onEditSource}>Edit source</button><span className="identity-pill">Locked source · {source?.source_id} · v{source?.source_version}</span></div>}
      {!sourceLocked && source && <div className="button-row"><button type="button" className="secondary-button" onClick={onCancelEdit}>Cancel edit</button></div>}
      {!generating && <><label>Existing AI-generated nursing note<textarea aria-label="Existing AI-generated note" aria-invalid={Boolean(noteError)} aria-describedby={noteError ? "existing-note-error" : undefined} value={existingNote} onChange={(event) => onExistingNote?.(event.target.value)} placeholder="Existing AI-generated nursing note …" /></label>{noteError && <p id="existing-note-error" className="field-error" role="alert">{noteError}</p>}</>}
      <div className="button-row">{action}</div>
    </StateCard>
  </div>;
}
