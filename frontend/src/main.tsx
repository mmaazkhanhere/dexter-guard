import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppProviders } from "./app/providers";
import { App } from "./app/App";
import { ErrorBoundary } from "./components/shared/ErrorBoundary";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders>
      <ErrorBoundary><App /></ErrorBoundary>
    </AppProviders>
  </StrictMode>,
);
