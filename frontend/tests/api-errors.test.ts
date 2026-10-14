import { expect, it } from "vitest";
import { apiErrorFromPayload } from "../src/api/errors";

it("translates technical generation errors into plain language while retaining the code internally", () => {
  const error = apiErrorFromPayload({
    code: "GENERATION_REJECTED",
    message: "A temporal qualifier is not supported by the source anchor.",
    field: "facts.0.temporalQualifier",
  }, 422);

  expect(error.message).toBe("The AI added a time detail that was not found in the transcript. Please check the transcript and try again.");
  expect(error.technicalMessage).toBe("A temporal qualifier is not supported by the source anchor.");
  expect(error.code).toBe("GENERATION_REJECTED");
  expect(error.field).toBe("facts.0.temporalQualifier");
});

it("keeps provider diagnostics separate from the friendly toast message", () => {
  const error = apiErrorFromPayload({
    code: "GENERATION_PROVIDER_FAILURE",
    message: "The generation provider failed.",
  }, 502);

  expect(error.message).toBe("The nursing note could not be generated right now. Please try again.");
  expect(error.technicalMessage).toBe("The generation provider failed.");
  expect(error.code).toBe("GENERATION_PROVIDER_FAILURE");
});
