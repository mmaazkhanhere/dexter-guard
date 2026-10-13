import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { DocumentationPage } from "../features/documentation/DocumentationPage";
import { EvaluationWorkspace } from "../features/evaluation/EvaluationWorkspace";
import { ReviewWorkspace } from "../features/review/ReviewWorkspace";
import { VerificationPage } from "../features/verification/VerificationPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/documentation" replace /> },
      { path: "documentation", element: <DocumentationPage /> },
      { path: "verification", element: <VerificationPage /> },
      { path: "review", element: <ReviewWorkspace /> },
      { path: "evaluation", element: <EvaluationWorkspace /> },
    ],
  },
]);
