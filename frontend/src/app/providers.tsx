import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { PropsWithChildren } from "react";
import { ToasterProvider } from "../components/shared/Toaster";
import { WorkspaceProvider } from "../state/workspace";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, retry: 1 } },
});

export function AppProviders({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}><WorkspaceProvider><ToasterProvider>{children}</ToasterProvider></WorkspaceProvider></QueryClientProvider>;
}
