import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { safeMutationError, useCreateSource, useFullVerification, useGenerateNote, useReview, useSavedExamples, useSource } from "../../api/hooks";
import type { NursingFact, NoteResponse, SourceDocument } from "../../api/types";
import { StateCard } from "../../components/shared/StateCard";
import { useToast } from "../../components/shared/Toaster";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { VerificationResults } from "../../features/verification/VerificationPage";
import { useWorkspace } from "../../state/workspace";
import { isDuplicateGeneratedNote, isTranscriptValid } from "./validation";

export function DocumentationVerificationPage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const { setSource, source, note, setNote, applyNoteRevision, setDraftContent } = useWorkspace();
  const examples = useSavedExamples();
  const createSource = useCreateSource();
  const generate = useGenerateNote();
  const fullVerification = useFullVerification();
  const review = useReview(note?.noteId, note?.revision);
  const [transcript, setTranscript] = useState("");
  const [residentId, setResidentId] = useState("synthetic-resident-demo");
  const [selectedExample, setSelectedExample] = useState("");
  const [isEditingSource, setIsEditingSource] = useState(false);
  const [generatedFacts, setGeneratedFacts] = useState<NursingFact[]>();
  const [generatedResidentId, setGeneratedResidentId] = useState<string>();
  const example = examples.data?.find((item) => item.exampleId === selectedExample);
  const sourceQuery = useSource(example?.sourceId, example?.sourceVersion);
  const error = examples.error ?? sourceQuery.error ?? createSource.error ?? generate.error ?? fullVerification.error;

  function clearCandidate() {
    setNote(undefined);
    setDraftContent(undefined);
    setGeneratedFacts(undefined);
    setGeneratedResidentId(undefined);
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
      notify({ tone: "success", title: "Saved example loaded", message: `“${example.title}” is now the locked source ${result.data.source_id}, version ${result.data.source_version}.` });
    } catch (actionError) {
      notifyFailure(notify, "Saved example could not be loaded", actionError, "The current transcript and candidate note were not changed.");
    }
  }

  async function sourceForGeneration(): Promise<SourceDocument | undefined> {
    if (source && !isEditingSource) return source;
    if (!isTranscriptValid(transcript)) return undefined;
    const result = await createSource.mutateAsync({ resident_test_id: residentId.trim(), language: "de-DE", transcript_text: transcript });
    setSource(result);
    setIsEditingSource(false);
    clearCandidate();
    return result;
  }

  async function verify(noteToVerify: NoteResponse): Promise<void> {
    const result = await fullVerification.mutateAsync({ noteId: noteToVerify.noteId, expectedRevision: noteToVerify.revision, reviewerLabel: "synthetic-reviewer" });
    if (result.status === "VALID") {
      notify({ tone: "success", title: "Generation and verification completed", message: `Note ${noteToVerify.noteId}, revision ${noteToVerify.revision}, is ready for Human Review. Backend approval eligibility remains authoritative.` });
    } else {
      notify({ tone: "error", title: `Verification ${result.status}`, message: `${result.failureMessage ?? "Verification did not complete successfully."} The candidate remains read-only and cannot be approved until Human Review resolves the backend state.` });
    }
  }

  async function generateAndVerify() {
    let activeSource: SourceDocument | undefined;
    try {
      activeSource = await sourceForGeneration();
    } catch (actionError) {
      notifyFailure(notify, "Transcript was not saved", actionError, "No candidate note was created.");
      return;
    }
    if (!activeSource) return;

    const reusableNote = note;
    if (reusableNote && isDuplicateGeneratedNote(reusableNote, activeSource, reusableNote.content, generatedFacts, generatedResidentId)) {
      const currentVerification = review.data?.fullVerification;
      if (currentVerification?.noteId === reusableNote.noteId && currentVerification.noteRevision === reusableNote.revision) {
        notify({ tone: "info", title: "Existing candidate reused", message: "The generated note, facts, resident, and source version are unchanged, so the current candidate and verification results were reused." });
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
      notify({ tone: "success", title: "Candidate note generated", message: `Note ${generated.noteId}, revision ${generated.revision}, was created for source ${generated.sourceId}, version ${generated.sourceVersion}. Full verification is starting now.` });
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

  const processing = createSource.isPending || generate.isPending || fullVerification.isPending;
  return <>
    <WorkspaceHeader eyebrow="01 · DOCUMENTATION & VERIFICATION" title="Create and check a candidate nursing note" description="Enter and check a synthetic German transcript, then generate and verify one source-bound candidate before Human Review." />
    {error && <div className="error-banner" role="alert">{safeMutationError(error).message} <span>({safeMutationError(error).code})</span></div>}
    <section className="documentation-verification-section" aria-label="Documentation and verification workflow">
      <StateCard title="Documentation & Verification" description="Enter and correct the transcript, then generate and verify the source-bound nursing note in this same workflow.">
        <div className="workflow-step">
          <h4>1. Enter and check the transcript</h4>
          <p className="workflow-step-description">Enter a synthetic transcript or load an example. Correct speech-to-text mistakes here before generating the note.</p>
          <label>Saved synthetic example<select aria-label="Saved synthetic example" disabled={Boolean(source) && !isEditingSource} value={selectedExample} onChange={(event) => setSelectedExample(event.target.value)}><option value="">Choose an example …</option>{examples.data?.map((item) => <option key={item.exampleId} value={item.exampleId}>{item.title}</option>)}</select></label><span className="field-description">Optional: load a saved synthetic scenario and its declared immutable source version.</span>
          <button className="secondary-button" onClick={loadExample} disabled={!example || sourceQuery.isFetching || Boolean(source) && !isEditingSource}>Load example</button>
          <label>Resident test ID<input readOnly={Boolean(source) && !isEditingSource} value={residentId} onChange={(event) => setResidentId(event.target.value)} /></label><span className="field-description">Use the synthetic resident identifier associated with this transcript.</span>
          <label>German transcript<textarea aria-label="German transcript" readOnly={Boolean(source) && !isEditingSource} required aria-invalid={!isTranscriptValid(transcript)} value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Deutsches synthetisches Transkript …" /></label><span className="field-description">{source && !isEditingSource ? "Locked source snapshot. Choose Edit source to create a new source after changing the text." : "Check and correct the text now. It is saved automatically when you choose Generate & Verify."}</span>
          <div className="button-row">{source && !isEditingSource && <button className="secondary-button" onClick={() => setIsEditingSource(true)}>Edit source</button>}{source && isEditingSource && <button className="secondary-button" onClick={() => { setTranscript(source.transcript_text); setResidentId(source.resident_test_id); setIsEditingSource(false); }}>Cancel edit</button>}</div>
          {source && <div className="identity-pill">Locked source snapshot · {source.source_id} · v{source.source_version} · {source.language}</div>}
        </div>
        <div className="workflow-step">
          <h4>2. Generate and verify</h4>
          <p className="workflow-step-description">Generate a professional draft and automatically run the complete backend verification workflow against this exact source version.</p>
          <p className="muted">The transcript is saved automatically if needed. The generated note stays read-only here; corrections belong in Human Review.</p>
          <button onClick={generateAndVerify} disabled={processing || !isTranscriptValid(transcript)}>{processing ? "Generating and verifying …" : "Generate & Verify"}</button>
          {note && <><div className="identity-pill">Candidate note · {note.noteId} · revision {note.revision} · {note.origin}</div><FactList facts={note.facts} /><button className="secondary-button" onClick={() => navigate("/review")}>Continue to Human Review</button></>}
        </div>
      </StateCard>
      {note && <div className="verification-results"><div className="verification-results-header"><span className="eyebrow">03 · RESULTS</span><h3>Inspect verification results</h3><p>Select a finding to see the affected note text, explanation, severity, and source-bound evidence. Corrections and approval remain in Human Review.</p></div><VerificationResults note={note} source={source} context={review.data} isLoading={review.isLoading || review.isFetching || fullVerification.isPending} /></div>}
    </section>
  </>;
}

function notifyFailure(notify: ReturnType<typeof useToast>["notify"], title: string, error: unknown, unchanged: string) {
  const detail = safeMutationError(error);
  notify({ tone: "error", title, message: `${detail.message} (code: ${detail.code}). ${unchanged}` });
}

function FactList({ facts }: { facts: NursingFact[] }) {
  const groups = ["OBSERVATION", "SYMPTOM", "MEASUREMENT", "ACTION"] as const;
  return <div className="facts"><h4>Structured facts returned by backend</h4>{groups.map((group) => <div key={group}><strong>{group}</strong>{facts.filter((fact) => fact.type === group).map((fact) => <p key={fact.factId}>{fact.statement}{fact.numericValue ? ` · ${fact.numericValue} ${fact.unit ?? ""}` : ""}</p>)}{facts.every((fact) => fact.type !== group) && <p className="muted">Absent</p>}</div>)}</div>;
}
