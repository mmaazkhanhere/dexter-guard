import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { safeMutationError, useCreateSource, useGenerateNote, useImportNote, useSavedExamples, useSource } from "../../api/hooks";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import { useToast } from "../../components/shared/Toaster";
import { useWorkspace } from "../../state/workspace";
import { isDuplicateGeneratedNote, isExternalNoteValid, isTranscriptValid } from "./validation";

export function DocumentationPage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const { setSource, source, note, setNote, applyNoteRevision, setDraftContent } = useWorkspace();
  const examples = useSavedExamples();
  const createSource = useCreateSource();
  const generate = useGenerateNote();
  const importNote = useImportNote();
  const [transcript, setTranscript] = useState("");
  const [residentId, setResidentId] = useState("synthetic-resident-demo");
  const [candidate, setCandidate] = useState("");
  const [selectedExample, setSelectedExample] = useState("");
  const [mode, setMode] = useState<"generate" | "import">("generate");
  const [isEditingSource, setIsEditingSource] = useState(false);
  const [generatedFacts, setGeneratedFacts] = useState<import("../../api/types").NursingFact[]>();
  const [generatedResidentId, setGeneratedResidentId] = useState<string>();
  const example = examples.data?.find((item) => item.exampleId === selectedExample);
  const sourceQuery = useSource(example?.sourceId, example?.sourceVersion);
  const error = examples.error ?? sourceQuery.error ?? createSource.error ?? generate.error ?? importNote.error;

  async function loadExample() {
    if (!example) return;
    try {
      const result = await sourceQuery.refetch();
      if (!result.data) throw result.error ?? new Error("The saved example did not return a source document.");
      setTranscript(result.data.transcript_text); setResidentId(result.data.resident_test_id); setCandidate(example.candidateNote ?? "");
      notify({ tone: "success", title: "Saved example loaded", message: `“${example.title}” loaded from source ${result.data.source_id}, version ${result.data.source_version}. No new source was created.` });
    } catch (actionError) {
      notifyFailure(notify, "Saved example could not be loaded", actionError, "The current transcript and candidate note were not changed.");
    }
  }
  async function submitTranscript() {
    if (!isTranscriptValid(transcript)) return;
    try {
      const result = await createSource.mutateAsync({ resident_test_id: residentId.trim(), language: "de-DE", transcript_text: transcript });
      setSource(result); setNote(undefined); setDraftContent(undefined); setGeneratedFacts(undefined); setGeneratedResidentId(undefined);
      setIsEditingSource(false);
      notify({ tone: "success", title: "Transcript saved", message: `Source ${result.source_id}, version ${result.source_version}, was created for ${result.resident_test_id} (${result.language}). Any previous candidate note was cleared.` });
    } catch (actionError) {
      notifyFailure(notify, "Transcript was not saved", actionError, "No source or candidate note was changed.");
    }
  }
  async function createNote() {
    if (!source) return;
    if (mode === "generate" && isDuplicateGeneratedNote(note, source, candidate, generatedFacts, generatedResidentId)) {
      notify({ tone: "info", title: "Candidate note already exists", message: "The note content, structured facts, resident, and source version are unchanged. No new generation was started." });
      return;
    }
    try {
      const result = mode === "generate"
        ? await generate.mutateAsync({ sourceId: source.source_id, sourceVersion: source.source_version, requestedBy: "synthetic-reviewer" })
        : await importNote.mutateAsync({ sourceId: source.source_id, sourceVersion: source.source_version, content: candidate, externalOrigin: { system: "synthetic-external-demo", externalNoteId: `external-${Date.now()}` }, requestedBy: "synthetic-reviewer", facts: [] });
      applyNoteRevision(result); setCandidate(result.content);
      if (mode === "generate") { setGeneratedFacts(result.facts); setGeneratedResidentId(source.resident_test_id); } else { setGeneratedFacts(undefined); setGeneratedResidentId(undefined); }
      const action = mode === "generate" ? "generated" : "imported";
      notify({ tone: "success", title: `Candidate note ${action}`, message: `Note ${result.noteId}, revision ${result.revision}, is a ${result.origin} draft for source ${result.sourceId}, version ${result.sourceVersion}. Run full verification before approval.` });
    } catch (actionError) {
      notifyFailure(notify, mode === "generate" ? "Note generation failed" : "Note import failed", actionError, "The current source and candidate note were not changed.");
    }
  }
  return <>
    <WorkspaceHeader eyebrow="01 · DOCUMENTATION" title="Create a candidate nursing note" description="Submit a synthetic German transcript, generate or import a candidate note, and preserve the source identity through review." />
    {error && <div className="error-banner" role="alert">{safeMutationError(error).message} <span>({safeMutationError(error).code})</span></div>}
    <div className="workspace-grid">
      <StateCard title="1. Add the source transcript" description="Load a saved synthetic example or enter the German transcript that will anchor the workflow. Next, submit it to create the immutable source record.">
        <label>Saved synthetic example<select aria-label="Saved synthetic example" disabled={Boolean(source) && !isEditingSource} value={selectedExample} onChange={(event) => setSelectedExample(event.target.value)}><option value="">Choose an example …</option>{examples.data?.map((item) => <option key={item.exampleId} value={item.exampleId}>{item.title}</option>)}</select></label><span className="field-description">Optional: choose a saved synthetic scenario, then load it into the transcript fields.</span>
        <button className="secondary-button" onClick={loadExample} disabled={!example || sourceQuery.isFetching || Boolean(source) && !isEditingSource}>Load example</button>
        <label>Resident test ID<input readOnly={Boolean(source) && !isEditingSource} value={residentId} onChange={(event) => setResidentId(event.target.value)} /></label><span className="field-description">Use the synthetic resident identifier associated with this transcript.</span>
        <label>German transcript<textarea aria-label="German transcript" readOnly={Boolean(source) && !isEditingSource} required aria-invalid={!isTranscriptValid(transcript)} value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Deutsches synthetisches Transkript …" /></label><span className="field-description">{source && !isEditingSource ? "Locked source snapshot. Choose Edit source to create a new source after changing the text." : "Paste the synthetic source text exactly as provided; it becomes the immutable evidence record."}</span>
        <div className="button-row"><button onClick={submitTranscript} disabled={createSource.isPending || !isTranscriptValid(transcript) || Boolean(source) && !isEditingSource}>{createSource.isPending ? "Saving …" : source ? "Save as new source" : "Submit transcript"}</button>{source && !isEditingSource && <button className="secondary-button" onClick={() => setIsEditingSource(true)}>Edit source</button>}{source && isEditingSource && <button className="secondary-button" onClick={() => { setTranscript(source.transcript_text); setResidentId(source.resident_test_id); setIsEditingSource(false); }}>Cancel edit</button>}</div>
        {source && <div className="identity-pill">Locked source snapshot · {source.source_id} · v{source.source_version} · {source.language}</div>}
      </StateCard>
      <StateCard title="2. Create the candidate note" description="Generate a draft from the submitted source or paste an external note. Next, inspect the returned facts and open Evidence Verification to check the draft.">
        <div className="segmented"><button className={mode === "generate" ? "selected" : ""} onClick={() => setMode("generate")}>Generate</button><button className={mode === "import" ? "selected" : ""} onClick={() => setMode("import")}>External note</button></div>
        <label>{mode === "generate" ? "Generated note preview" : "External candidate note"}<textarea aria-label="Candidate nursing note" value={candidate} onChange={(event) => setCandidate(event.target.value)} placeholder="Kandidatennotiz …" /></label><span className="field-description">{mode === "generate" ? "Review the generated draft after creating it; it remains editable until verification." : "Paste a synthetic note from another source, then import it for verification."}</span>
        <button onClick={createNote} disabled={!source || isEditingSource || generate.isPending || importNote.isPending || (mode === "import" && !isExternalNoteValid(candidate))}>{generate.isPending || importNote.isPending ? "Working …" : mode === "generate" ? "Generate nursing note" : "Import note"}</button>
        {note && <><div className="identity-pill">Note {note.noteId} · revision {note.revision} · {note.origin}</div><FactList facts={note.facts} /><button className="secondary-button" onClick={() => navigate("/verification")}>Open verification</button></>}
      </StateCard>
    </div>
  </>;
}

function notifyFailure(notify: ReturnType<typeof useToast>["notify"], title: string, error: unknown, unchanged: string) {
  const detail = safeMutationError(error);
  notify({ tone: "error", title, message: `${detail.message} (code: ${detail.code}). ${unchanged}` });
}

function FactList({ facts }: { facts: import("../../api/types").NursingFact[] }) {
  const groups = ["OBSERVATION", "SYMPTOM", "MEASUREMENT", "ACTION"] as const;
  return <div className="facts"><h4>Structured facts returned by backend</h4>{groups.map((group) => <div key={group}><strong>{group}</strong>{facts.filter((fact) => fact.type === group).map((fact) => <p key={fact.factId}>{fact.statement}{fact.numericValue ? ` · ${fact.numericValue} ${fact.unit ?? ""}` : ""}</p>)}{facts.every((fact) => fact.type !== group) && <p className="muted">Absent</p>}</div>)}</div>;
}
