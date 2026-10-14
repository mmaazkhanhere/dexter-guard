import { expect, it } from "vitest";
import { apiErrorFromPayload } from "../src/api/errors";

it("translates technical generation errors into plain language while retaining the code internally", () => {
  const error = apiErrorFromPayload({
    code: "GENERATION_REJECTED",
    message: "A temporal qualifier is not supported by the source anchor.",
    field: "facts.0.temporalQualifier",
  }, 422);

  expect(error.message).toBe("The AI added a time detail that was not found in the transcript. Please check the transcript and try again.");
  expect(error.code).toBe("GENERATION_REJECTED");
  expect(error.field).toBe("facts.0.temporalQualifier");
});
