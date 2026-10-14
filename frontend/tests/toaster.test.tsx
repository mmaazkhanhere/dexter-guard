import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { ToasterProvider, useToast } from "../src/components/shared/Toaster";

function NotificationTrigger() {
  const { notify } = useToast();
  return <button onClick={() => notify({ tone: "error", title: "Verification could not run", message: "The service is temporarily unavailable. Please try again. Approval remains blocked." })}>Notify</button>;
}

it("announces an actionable error and lets the reviewer dismiss it", async () => {
  const user = userEvent.setup();
  render(<ToasterProvider><NotificationTrigger /></ToasterProvider>);

  await user.click(screen.getByRole("button", { name: "Notify" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Verification could not run");
  expect(screen.getByRole("alert")).toHaveTextContent("The service is temporarily unavailable. Please try again.");
  expect(screen.getByRole("alert")).toHaveTextContent("Approval remains blocked");

  await user.click(screen.getByRole("button", { name: /Dismiss notification: Verification could not run/ }));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
