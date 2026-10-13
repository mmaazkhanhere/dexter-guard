import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { DocumentationPage } from "../features/documentation/DocumentationPage";
import { EvaluationDashboard } from "../features/evaluation/EvaluationDashboard";
import { ReviewPage } from "../features/review/ReviewPage";
import { VerificationPage } from "../features/verification/VerificationPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/documentation" replace /> },
      { path: "documentation", element: <DocumentationPage /> },
      { path: "verification", element: <VerificationPage /> },
      { path: "review", element: <ReviewPage /> },
      { path: "evaluation", element: <EvaluationDashboard /> },
    ],
  },
]);
