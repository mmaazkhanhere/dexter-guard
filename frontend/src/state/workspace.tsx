import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";
import type { NoteResponse, SourceDocument } from "../api/types";

type WorkspaceState = { source?: SourceDocument; note?: NoteResponse; setSource: (source?: SourceDocument) => void; setNote: (note?: NoteResponse) => void };
const WorkspaceContext = createContext<WorkspaceState | null>(null);

export function WorkspaceProvider({ children }: PropsWithChildren) {
  const [source, setSource] = useState<SourceDocument>();
  const [note, setNote] = useState<NoteResponse>();
  const value = useMemo(() => ({ source, note, setSource, setNote }), [source, note]);
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() { const value = useContext(WorkspaceContext); if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider"); return value; }
