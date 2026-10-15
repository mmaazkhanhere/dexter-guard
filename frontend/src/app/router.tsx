import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { DocumentationVerificationWorkspace } from "../features/documentation/DocumentationVerificationWorkspace";
import { EvaluationWorkspace } from "../features/evaluation/EvaluationWorkspace";
import { ReviewWorkspace } from "../features/review/ReviewWorkspace";
import { FounderDemoPage } from "../features/demo/FounderDemoPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <FounderDemoPage /> },
      { path: "demo", element: <Navigate to="/" replace /> },
      { path: "documentation", element: <DocumentationVerificationWorkspace /> },
      { path: "verification", element: <Navigate to="/documentation" replace /> },
      { path: "review", element: <ReviewWorkspace /> },
      { path: "evaluation", element: <EvaluationWorkspace /> },
    ],
  },
]);
