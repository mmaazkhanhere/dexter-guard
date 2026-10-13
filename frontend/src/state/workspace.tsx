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
  setSource: (source?: SourceDocument) => void;
  setNote: (note?: NoteResponse) => void;
  setDraftContent: (content?: string) => void;
  applyNoteRevision: (note: NoteResponse) => boolean;
};
const WorkspaceContext = createContext<WorkspaceState | null>(null);

export function WorkspaceProvider({ children }: PropsWithChildren) {
  const [source, setSource] = useState<SourceDocument>();
  const [note, setNote] = useState<NoteResponse>();
  const [draftContent, setDraftContent] = useState<string>();
  const noteRef = useRef(note);
  noteRef.current = note;
  const applyNoteRevision = (candidate: NoteResponse) => {
    if (!shouldApplyNoteRevision(noteRef.current, candidate)) return false;
    noteRef.current = candidate;
    setNote(candidate);
    setDraftContent(candidate.content);
    return true;
  };
  const value = useMemo(() => ({ source, note, draftContent, setSource, setNote, setDraftContent, applyNoteRevision }), [source, note, draftContent]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() { const value = useContext(WorkspaceContext); if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider"); return value; }
