import { createContext, useContext, useMemo, useRef, useState, type PropsWithChildren } from "react";
import type { NoteResponse, SourceDocument } from "../api/types";

export function shouldApplyNoteRevision(current: NoteResponse | undefined, candidate: NoteResponse): boolean {
  if (!current) return true;
  if (current.noteId !== candidate.noteId) return false;
  return candidate.revision >= current.revision;
}

type WorkspaceState = {
  source?: SourceDocument;
  note?: NoteResponse;
  draftContent?: string;
  transcript?: string;
  residentId?: string;
  setSource: (source?: SourceDocument) => void;
  setNote: (note?: NoteResponse) => void;
  setDraftContent: (content?: string) => void;
  setTranscript: (transcript?: string) => void;
  setResidentId: (residentId?: string) => void;
  applyNoteRevision: (note: NoteResponse) => boolean;
};
const WorkspaceContext = createContext<WorkspaceState | null>(null);

export function WorkspaceProvider({ children }: PropsWithChildren) {
  const [source, setSource] = useState<SourceDocument>();
  const [note, setNoteState] = useState<NoteResponse>();
  const [draftContent, setDraftContent] = useState<string>();
  const [transcript, setTranscript] = useState<string>();
  const [residentId, setResidentId] = useState<string>();
  const noteRef = useRef(note);
  noteRef.current = note;
  const setSourceAndIdentity = (candidate?: SourceDocument) => {
    setSource(candidate);
    if (candidate) {
      setTranscript(candidate.transcript_text);
      setResidentId(candidate.resident_test_id);
    }
  };
  const setNote = (candidate?: NoteResponse) => {
    noteRef.current = candidate;
    setNoteState(candidate);
  };
  const applyNoteRevision = (candidate: NoteResponse) => {
    if (!shouldApplyNoteRevision(noteRef.current, candidate)) return false;
    setNote(candidate);
    setDraftContent(candidate.content);
    return true;
  };
  const value = useMemo(() => ({ source, note, draftContent, transcript, residentId, setSource: setSourceAndIdentity, setNote, setDraftContent, setTranscript, setResidentId, applyNoteRevision }), [source, note, draftContent, transcript, residentId]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() { const value = useContext(WorkspaceContext); if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider"); return value; }
