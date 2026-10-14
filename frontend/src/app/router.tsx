import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { DocumentationVerificationPage } from "../features/documentation/DocumentationVerificationPage";
import { EvaluationWorkspace } from "../features/evaluation/EvaluationWorkspace";
import { ReviewWorkspace } from "../features/review/ReviewWorkspace";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/documentation" replace /> },
      { path: "documentation", element: <DocumentationVerificationPage /> },
      { path: "verification", element: <Navigate to="/documentation" replace /> },
      { path: "review", element: <ReviewWorkspace /> },
      { path: "evaluation", element: <EvaluationWorkspace /> },
    ],
  },
]);
