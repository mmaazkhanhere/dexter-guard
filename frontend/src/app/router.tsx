import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { DocumentationVerificationWorkspace } from "../features/documentation/DocumentationVerificationWorkspace";
import { EvaluationWorkspace } from "../features/evaluation/EvaluationWorkspace";
import { ReviewWorkspace } from "../features/review/ReviewWorkspace";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/documentation" replace /> },
      { path: "documentation", element: <DocumentationVerificationWorkspace /> },
      { path: "verification", element: <Navigate to="/documentation" replace /> },
      { path: "review", element: <ReviewWorkspace /> },
      { path: "evaluation", element: <EvaluationWorkspace /> },
    ],
  },
]);
