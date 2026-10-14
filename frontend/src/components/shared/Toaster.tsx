import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from "react";

export type ToastTone = "success" | "error" | "info";

type ToastInput = {
  title: string;
  message: string;
  tone?: ToastTone;
};

type Toast = ToastInput & { id: number; tone: ToastTone };

type ToastContextValue = {
  notify: (toast: ToastInput) => void;
  dismiss: (id: number) => void;
};

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToasterProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((toast) => toast.id !== id)), []);
  const notify = useCallback((input: ToastInput) => {
    const toast = { ...input, id: Date.now() + Math.random(), tone: input.tone ?? "info" };
    setToasts((current) => [...current, toast].slice(-4));
  }, []);
  const value = useMemo(() => ({ notify, dismiss }), [dismiss, notify]);

  return <ToastContext.Provider value={value}>{children}<ToastRegion toasts={toasts} dismiss={dismiss} /></ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToasterProvider");
  return context;
}

function ToastRegion({ toasts, dismiss }: { toasts: Toast[]; dismiss: (id: number) => void }) {
  return <section className="toast-region" aria-label="Action notifications" aria-live="polite" aria-relevant="additions">
    {toasts.map((toast) => <ToastMessage key={toast.id} toast={toast} dismiss={dismiss} />)}
  </section>;
}

function ToastMessage({ toast, dismiss }: { toast: Toast; dismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = window.setTimeout(() => dismiss(toast.id), toast.tone === "error" ? 10_000 : 6_000);
    return () => window.clearTimeout(timer);
  }, [dismiss, toast.id, toast.tone]);

  return <div className={`toast toast-${toast.tone}`} role={toast.tone === "error" ? "alert" : "status"}>
    <div><strong>{toast.title}</strong><p>{toast.message}</p></div>
    <button type="button" className="toast-dismiss" aria-label={`Dismiss notification: ${toast.title}`} onClick={() => dismiss(toast.id)}>Dismiss</button>
  </div>;
}
