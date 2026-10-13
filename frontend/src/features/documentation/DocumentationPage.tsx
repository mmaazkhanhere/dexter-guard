import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { safeMutationError, useCreateSource, useGenerateNote, useImportNote, useSavedExamples, useSource } from "../../api/hooks";
import { WorkspaceHeader } from "../../components/shared/WorkspaceHeader";
import { StateCard } from "../../components/shared/StateCard";
import { useWorkspace } from "../../state/workspace";
import { isExternalNoteValid, isTranscriptValid } from "./validation";

export function DocumentationPage() {
  const navigate = useNavigate();
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
  const example = examples.data?.find((item) => item.exampleId === selectedExample);
  const sourceQuery = useSource(example?.sourceId, example?.sourceVersion);
  const error = examples.error ?? sourceQuery.error ?? createSource.error ?? generate.error ?? importNote.error;

  async function loadExample() {
    if (!example) return;
    const result = await sourceQuery.refetch();
    if (result.data) { setTranscript(result.data.transcript_text); setResidentId(result.data.resident_test_id); setCandidate(example.candidateNote ?? ""); }
  }
  async function submitTranscript() {
    if (!isTranscriptValid(transcript)) return;
    const result = await createSource.mutateAsync({ resident_test_id: residentId.trim(), language: "de-DE", transcript_text: transcript });
    setSource(result); setNote(undefined); setDraftContent(undefined);
  }
  async function createNote() {
    if (!source) return;
    const result = mode === "generate"
      ? await generate.mutateAsync({ sourceId: source.source_id, sourceVersion: source.source_version, requestedBy: "synthetic-reviewer" })
      : await importNote.mutateAsync({ sourceId: source.source_id, sourceVersion: source.source_version, content: candidate, externalOrigin: { system: "synthetic-external-demo", externalNoteId: `external-${Date.now()}` }, requestedBy: "synthetic-reviewer", facts: [] });
    applyNoteRevision(result); setCandidate(result.content);
  }
  return <>
    <WorkspaceHeader eyebrow="01 · DOCUMENTATION" title="Create a candidate nursing note" description="Submit a synthetic German transcript, generate or import a candidate note, and preserve the source identity through review." />
    {error && <div className="error-banner" role="alert">{safeMutationError(error).message} <span>({safeMutationError(error).code})</span></div>}
    <div className="workspace-grid">
      <StateCard title="Transcript input">
        <label>Saved synthetic example<select aria-label="Saved synthetic example" value={selectedExample} onChange={(event) => setSelectedExample(event.target.value)}><option value="">Choose an example …</option>{examples.data?.map((item) => <option key={item.exampleId} value={item.exampleId}>{item.title}</option>)}</select></label>
        <button className="secondary-button" onClick={loadExample} disabled={!example || sourceQuery.isFetching}>Load example</button>
        <label>Resident test ID<input value={residentId} onChange={(event) => setResidentId(event.target.value)} /></label>
        <label>German transcript<textarea aria-label="German transcript" required aria-invalid={!isTranscriptValid(transcript)} value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Deutsches synthetisches Transkript …" /></label>
        <button onClick={submitTranscript} disabled={createSource.isPending || !isTranscriptValid(transcript)}>{createSource.isPending ? "Submitting …" : "Submit transcript"}</button>
        {source && <div className="identity-pill">Source {source.source_id} · v{source.source_version} · {source.language}</div>}
      </StateCard>
      <StateCard title="Candidate note">
        <div className="segmented"><button className={mode === "generate" ? "selected" : ""} onClick={() => setMode("generate")}>Generate</button><button className={mode === "import" ? "selected" : ""} onClick={() => setMode("import")}>External note</button></div>
        <label>{mode === "generate" ? "Generated note preview" : "External candidate note"}<textarea aria-label="Candidate nursing note" value={candidate} onChange={(event) => setCandidate(event.target.value)} placeholder="Kandidatennotiz …" /></label>
        <button onClick={createNote} disabled={!source || generate.isPending || importNote.isPending || (mode === "import" && !isExternalNoteValid(candidate))}>{generate.isPending || importNote.isPending ? "Working …" : mode === "generate" ? "Generate nursing note" : "Import note"}</button>
        {note && <><div className="identity-pill">Note {note.noteId} · revision {note.revision} · {note.origin}</div><FactList facts={note.facts} /><button className="secondary-button" onClick={() => navigate("/verification")}>Open verification</button></>}
      </StateCard>
    </div>
  </>;
}

function FactList({ facts }: { facts: import("../../api/types").NursingFact[] }) {
  const groups = ["OBSERVATION", "SYMPTOM", "MEASUREMENT", "ACTION"] as const;
  return <div className="facts"><h4>Structured facts returned by backend</h4>{groups.map((group) => <div key={group}><strong>{group}</strong>{facts.filter((fact) => fact.type === group).map((fact) => <p key={fact.factId}>{fact.statement}{fact.numericValue ? ` · ${fact.numericValue} ${fact.unit ?? ""}` : ""}</p>)}{facts.every((fact) => fact.type !== group) && <p className="muted">Absent</p>}</div>)}</div>;
}
